import json
import re
import asyncio
import os
import hashlib
import ast
import time
import threading
from concurrent.futures import ThreadPoolExecutor
from agent import Agent
import tools

class ClaimRegistry:
    def __init__(self):
        self.lock = threading.Lock()
        self.claims = {}          # norm_path -> worker_id
        self.contested = []       # list of (norm_path, worker_id, existing_worker_id)

    def claim(self, file_path: str, worker_id: str):
        norm_path = os.path.normpath(file_path)
        with self.lock:
            if norm_path in self.claims:
                existing = self.claims[norm_path]
                if existing != worker_id:
                    self.contested.append((norm_path, worker_id, existing))
                    print(f"\n[CLAIM REGISTRY] WARNING: Contested claim! Worker-{worker_id} intends to touch {norm_path} (already claimed by Worker-{existing}).")
            else:
                self.claims[norm_path] = worker_id

def parse_planner_response(content: str, fallback_request: str) -> dict:
    """Parses the planner's JSON response, stripping markdown fences and falling back on error."""
    cleaned = content.strip()
    
    # Strip markdown code block fences if present
    if cleaned.startswith("```"):
        match = re.match(r"^```(?:json)?\s*(.*?)\s*```$", cleaned, re.DOTALL)
        if match:
            cleaned = match.group(1).strip()
        else:
            first_nl = cleaned.find("\n")
            if first_nl != -1:
                cleaned = cleaned[first_nl:].strip()
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3].strip()

    try:
        data = json.loads(cleaned)
        if "subtasks" in data and isinstance(data["subtasks"], list):
            return data
    except Exception:
        pass

    return {
        "subtasks": [
            {
                "id": "1",
                "title": "Process user task",
                "instructions": fallback_request
            }
        ]
    }

class Orchestrator:
    def __init__(self, client=None, model: str = None, tools: list = None, providers: list = None):
        """Initializes the Orchestrator.
        
        Args:
            client: Backward-compatible single Groq/OpenAI client instance.
            model: Backward-compatible model name.
            tools: List of tool functions to provide to workers.
            providers: List of provider configurations.
        """
        self.tools = tools or []
        if client:
            self.providers = [{
                "name": "mock",
                "client": client,
                "model": model or "llama-3.3-70b-versatile"
            }]
        else:
            self.providers = providers or []

    def _send_completion_with_retry(self, messages, response_format=None):
        """Helper to send chat completion with multi-provider fallback and retry logic."""
        max_retries = 3
        base_backoff = 10
        num_providers = len(self.providers)
        
        if num_providers == 0:
            raise ValueError("No providers configured. Please set GROQ_API_KEY or NVIDIA_API_KEY.")
            
        for attempt in range(max_retries + 1):
            for offset in range(num_providers):
                provider = self.providers[offset]
                p_name = provider["name"]
                p_client = provider["client"]
                p_model = provider["model"]
                
                try:
                    kwargs = {
                        "model": p_model,
                        "messages": messages
                    }
                    if response_format:
                        kwargs["response_format"] = response_format
                        
                    response = p_client.chat.completions.create(**kwargs)
                    return response.choices[0].message.content or ""
                    
                except Exception as e:
                    status_code = getattr(e, "status_code", None)
                    is_transient = True
                    if status_code in (400, 401, 403, 404, 422):
                        is_transient = False
                    
                    if is_transient and num_providers > 1 and offset < num_providers - 1:
                        next_provider = self.providers[offset + 1]
                        print(f"\n[Orchestrator] WARNING: {p_name} failed (status {status_code or 'error'}). Falling back immediately to {next_provider['name']}...")
                        continue
                        
                    if offset == num_providers - 1:
                        if attempt < max_retries:
                            if not is_transient:
                                raise e
                            delay = base_backoff * (2 ** attempt)
                            time.sleep(delay)
                        else:
                            raise e

    def plan(self, user_request: str) -> list:
        """Asks the planner model to break down the task into subtasks."""
        planner_prompt = f"""You are a software architect task planner.
Your job is to break down the user's coding request into 1 to 4 independent subtasks that can be executed in parallel.
For each subtask, provide:
- id: A unique string identifier starting from "1"
- title: A short description of the subtask
- instructions: Detailed, step-by-step instructions for a senior developer agent to implement this subtask.

You MUST return ONLY a JSON object of this exact schema. Do not output any markdown code blocks or additional text:
{{
  "subtasks": [
    {{
      "id": "1",
      "title": "Subtask Title",
      "instructions": "Instructions here..."
    }}
  ]
}}

User request: {user_request}"""

        try:
            messages = [{"role": "user", "content": planner_prompt}]
            text = self._send_completion_with_retry(messages, response_format={"type": "json_object"})
        except Exception as e:
            text = f"ERROR: {str(e)}"

        data = parse_planner_response(text, user_request)
        return data.get("subtasks", [])

    async def run_workers(self, subtasks: list, on_tool_call=None) -> tuple[dict, list]:
        """Runs the worker agents concurrently using a ThreadPoolExecutor.
        
        Returns:
            A tuple of (results, conflicts) where conflicts is a list of detected write conflicts.
        """
        loop = asyncio.get_running_loop()
        
        # Instantiate thread-safe claim registry
        registry = ClaimRegistry()

        def make_wrapped_write_file(worker_id):
            def wrapped_write_file(path: str, content: str) -> str:
                registry.claim(path, worker_id)
                return tools.write_file(path, content)
            wrapped_write_file.__name__ = "write_file"
            return wrapped_write_file

        # Snapshot initial files in the workspace
        initial_files = {}
        for root, dirs, files in os.walk("."):
            if any(p in root for p in ("venv", ".git", "__pycache__", ".system_generated", "race_test_scratch")):
                continue
            for f in files:
                rel_path = os.path.normpath(os.path.join(root, f))
                try:
                    with open(rel_path, "r", encoding="utf-8") as file_obj:
                        initial_files[rel_path] = file_obj.read()
                except Exception:
                    pass

        with ThreadPoolExecutor(max_workers=max(1, len(subtasks))) as executor:
            futures = []
            for subtask in subtasks:
                worker_tools = []
                for t in self.tools:
                    if t.__name__ == "write_file":
                        worker_tools.append(make_wrapped_write_file(subtask["id"]))
                    else:
                        worker_tools.append(t)

                agent = Agent(
                    name=f"Worker-{subtask['id']}",
                    role=subtask["title"],
                    system_instruction=f"""You are a senior developer agent working on a subtask: '{subtask['title']}'.
Instructions:
{subtask['instructions']}

You have access to file and shell tools in the workspace directory.
You MUST write real working code (not pseudocode) and must finish with a plain-text summary of your actions once done.
Do not call any tools after your final summary.""",
                    providers=self.providers,
                    tools=worker_tools,
                    on_tool_call=on_tool_call
                )
                
                future = loop.run_in_executor(
                    executor,
                    agent.run,
                    subtask["instructions"]
                )
                futures.append((subtask["id"], future))

            results = {}
            agent_writes = {}
            for subtask_id, future in futures:
                text, writes = await future
                results[subtask_id] = text
                agent_writes[subtask_id] = writes

            # Map from file path to list of writes by different agents
            file_writes = {}
            for worker_id, writes in agent_writes.items():
                for w in writes:
                    norm_path = os.path.normpath(w["path"])
                    file_writes.setdefault(norm_path, []).append((worker_id, w))

            # Detect collisions and perform automatic merge resolution (v3)
            conflicts = []
            for path, writes_list in file_writes.items():
                if len(writes_list) > 1:
                    final_hash = None
                    if os.path.exists(path):
                        try:
                            with open(path, "r", encoding="utf-8") as f:
                                final_content = f.read()
                                final_hash = hashlib.sha256(final_content.encode("utf-8")).hexdigest()
                        except Exception:
                            pass
                    
                    winners = []
                    losers = []
                    for worker_id, w in writes_list:
                        if final_hash and w["hash"] == final_hash:
                            winners.append(worker_id)
                        else:
                            losers.append((worker_id, w))

                    resolved = False
                    merged_content = None
                    merge_error = None

                    if os.path.exists(path):
                        initial_content = initial_files.get(path, "")
                        subtask_map = {st["id"]: st for st in subtasks}

                        try:
                            prompt = f"""You are a senior software conflict resolution reconciler.
Your task is to merge multiple divergent versions of a file into a single resolved version.
Below is the original file content, followed by the divergent versions written by different developer agents, along with their respective instructions explaining the intent of their changes.

Original File Content:
---
{initial_content}
---

Divergent Versions:
"""
                            for worker_id, w in writes_list:
                                instr = subtask_map.get(worker_id, {}).get("instructions", "No instructions provided.")
                                prompt += f"\nVersion by Worker-{worker_id} (Instructions: {instr}):\n"
                                prompt += f"---\n{w['content']}\n---\n"

                            prompt += """
Please merge these changes into a single file that preserves the INTENT of all edits (e.g. if one worker removed routes, another added logging, and a third refactored database initialization, all these edits should be cleanly combined).
Ensure the output is syntactically valid and compiles.
You must return the full merged file content inside a markdown code block starting with ```python (or the appropriate language fence). Do not output any other reasoning or extra text.
"""
                            messages = [{"role": "user", "content": prompt}]
                            response_text = self._send_completion_with_retry(messages)

                            # Extract code content
                            raw_merged = response_text.strip()
                            if "```" in raw_merged:
                                match = re.search(r"```(?:\w+)?\s*(.*?)\s*```", raw_merged, re.DOTALL)
                                if match:
                                    merged_content = match.group(1).strip()
                                else:
                                    merged_content = raw_merged
                            else:
                                merged_content = raw_merged

                            if path.endswith(".py"):
                                try:
                                    ast.parse(merged_content)
                                except SyntaxError as se:
                                    raise ValueError(f"Merged output has invalid Python syntax: {se}")

                            is_identical = False
                            for worker_id, w in writes_list:
                                if merged_content == w["content"]:
                                    is_identical = True
                                    break
                            if is_identical:
                                raise ValueError("Merged output is byte-identical to one of the original inputs (failed to combine changes)")

                            with open(path, "w", encoding="utf-8") as f_out:
                                f_out.write(merged_content)
                            resolved = True

                        except Exception as ex:
                            merge_error = str(ex)
                            resolved = False
                            merged_content = None

                    conflicts.append({
                        "path": path,
                        "workers": [worker_id for worker_id, _ in writes_list],
                        "winners": winners,
                        "losers": losers,
                        "resolved": resolved,
                        "merged_content": merged_content,
                        "error": merge_error
                    })

            return results, conflicts
