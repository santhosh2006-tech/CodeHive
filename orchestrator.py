import json
import re
import asyncio
import os
import ast
import time
import threading
import subprocess
import shutil
import inspect
from concurrent.futures import ThreadPoolExecutor
from agent import Agent
import tools

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

    def _create_chat_completion(self, client, kwargs: dict, request_timeout: float | None):
        """Call chat completions with a per-request timeout when the SDK supports it."""
        if request_timeout is not None:
            try:
                sig = inspect.signature(client.chat.completions.create)
                supports_timeout = (
                    "timeout" in sig.parameters or
                    any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values())
                )
            except Exception:
                supports_timeout = True

            if supports_timeout:
                kwargs = dict(kwargs)
                kwargs["timeout"] = request_timeout

        return client.chat.completions.create(**kwargs)

    def _send_completion_with_retry(
        self,
        messages,
        response_format=None,
        max_retries: int = 3,
        base_backoff: int = 10,
        request_timeout: float | None = 30.0,
        fallback_on_client_error: bool = False,
    ):
        """Helper to send chat completion with multi-provider fallback and retry logic."""
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
                        
                    response = self._create_chat_completion(p_client, kwargs, request_timeout)
                    return response.choices[0].message.content or ""
                    
                except Exception as e:
                    status_code = getattr(e, "status_code", None)
                    is_transient = True
                    if status_code in (400, 401, 403, 404, 422):
                        is_transient = False
                    
                    should_fallback = is_transient or fallback_on_client_error
                    if should_fallback and num_providers > 1 and offset < num_providers - 1:
                        next_provider = self.providers[offset + 1]
                        print(f"\n[{p_name}] WARNING: {p_name} failed (status {status_code or 'error'}). Falling back immediately to {next_provider['name']}...")
                        continue
                        
                    if offset == num_providers - 1:
                        if attempt < max_retries:
                            if not is_transient:
                                raise e
                            delay = base_backoff * (2 ** attempt)
                            last_err = str(e)
                            print(f"\n[{p_name}] WARNING: All providers failed. Retrying in {delay} seconds (attempt {attempt + 1}/{max_retries}). Last error: {last_err}")
                            time.sleep(delay)
                        else:
                            raise e

    def _reconcile_conflict(self, path: str, conf_content: str) -> str:
        """Invokes the LLM reconciler to resolve merge conflict markers inside a file.
        Only called when git reports a real merge conflict (<<<<<<< markers present).
        """
        prompt = f"""You are a senior software conflict resolution reconciler.
Your task is to merge the conflicting edits in a file containing Git conflict markers into a single resolved version.
Preserve the intent of BOTH sides of the conflict. Do not add new imports, classes, or functions that are not present in either side.

Conflicted File Content:
---
{conf_content}
---

You must return ONLY the full resolved file content inside a markdown code block (e.g. ```python). Do not output any other reasoning or extra text.
"""
        messages = [{"role": "user", "content": prompt}]
        return self._send_completion_with_retry(messages)

    def get_preflight_warnings(self, subtasks: list) -> list[str]:
        """Runs a pre-flight sanity check on instructions to identify potential over-splitting.
        If two or more subtasks reference the same filename, a warning is returned.
        """
        file_pattern = re.compile(r'\b[\w\-]+\.(?:py|html|css|js|json|md|txt|sh|bat)\b', re.IGNORECASE)
        
        file_references = {}
        for st in subtasks:
            st_id = st.get("id", "unknown")
            instr = st.get("instructions", "")
            found_files = set(file_pattern.findall(instr))
            for filename in found_files:
                file_references.setdefault(filename.lower(), []).append((st_id, filename))
                
        warnings = []
        for filename_lower, refs in file_references.items():
            if len(refs) > 1:
                st_ids = [r[0] for r in refs]
                original_name = refs[0][1]
                warnings.append(
                    f"[Planner] WARNING: {len(st_ids)} subtasks all reference {original_name} "
                    f"(Subtasks: {', '.join(st_ids)}) \u2014 this task may have been over-split."
                )
        return warnings

    def plan(self, user_request: str, history: list = None) -> list:
        """Asks the planner model to break down the task into subtasks."""
        history_str = ""
        if history:
            history_str = "--- CONVERSATION HISTORY ---\n"
            for turn in history:
                role_label = "User" if turn.get("role") == "user" else "Assistant (CodeHive)"
                content = turn.get("content", "")
                history_str += f"{role_label}: {content}\n\n"
            history_str += "--- END OF CONVERSATION HISTORY ---\n\n"

        planner_prompt = f"""You are a software architect task planner.
Your job is to break down the user's coding request into 1 to 4 subtasks.

--- SPLITTING RULES ---
Only create MULTIPLE subtasks when components are GENUINELY INDEPENDENT:
1. The task centers on a single file or a small number of tightly-related files where changes are naturally sequential, interdependent, or overlapping (e.g. "a module with a few functions" is one single coherent unit of work, NOT one subtask per function).
2. The task is small enough that a single developer would write it top-to-bottom in one sitting, rather than collaborating with others.
3. Splitting would require two or more agents to edit or touch the same file to complete their subtask.

Only split into multiple subtasks when the components are GENUINELY INDEPENDENT:
- Separate files that do not read or modify each other's code.
- Genuinely separate concerns (e.g. "Backend API endpoint" + "separate testing script file").
- "The add function" + "the subtract function" in the same file is NOT a valid split—that must be a single subtask.

--- CONTENT DEPENDENCY SEQUENCING ---
Some subtasks are CONTENT-DEPENDENT even when they touch different files:
1. **Tests & Docs**: A test file depends on the real implementation it tests; documentation depends on the real API/interface it describes.
2. **Calling/Integration Imports**: If one subtask implements a core function, class, or module and another subtask implements an interface or API that imports/calls it, the caller subtask MUST depend on the implementer subtask.

These are NOT independent, even though they are separate files. You MUST order the dependent subtask to run AFTER the subtask(s) it depends on by referencing its ID in the "depends_on" array.

You MUST return ONLY a JSON object of this exact schema. Do not output any markdown code blocks or additional text:
{{
  "subtasks": [
    {{
      "id": "1",
      "title": "Subtask Title",
      "instructions": "Instructions here...",
      "depends_on": []
    }},
    {{
      "id": "2",
      "title": "Subtask 2 Title",
      "instructions": "Instructions here...",
      "depends_on": ["1"]
    }}
  ]
}}

{history_str}User request: {user_request}"""

        try:
            messages = [{"role": "user", "content": planner_prompt}]
            text = self._send_completion_with_retry(
                messages,
                response_format={"type": "json_object"},
                max_retries=0,
                request_timeout=30.0,
                fallback_on_client_error=True,
            )
        except Exception as e:
            text = f"ERROR: {str(e)}"

        data = parse_planner_response(text, user_request)
        return data.get("subtasks", [])

    async def run_workers(self, subtasks: list, on_tool_call=None, history: list = None) -> tuple[dict, list, list]:
        """Runs the worker agents concurrently in dependency waves using Git worktrees.
        
        Returns:
            A tuple of (results, conflicts, execution_warnings).
        """
        loop = asyncio.get_running_loop()
        subtask_map = {st["id"]: st for st in subtasks}

        # Stage 1: Git repo check & auto-init
        if not os.path.exists(".git"):
            subprocess.run("git init", shell=True, capture_output=True, text=True)
            subprocess.run('git config user.name "CodeHive Agent"', shell=True, capture_output=True, text=True)
            subprocess.run('git config user.email "agent@codehive.local"', shell=True, capture_output=True, text=True)
            subprocess.run("git add -A", shell=True, capture_output=True, text=True)
            subprocess.run('git commit -m "Initial commit by CodeHive"', shell=True, capture_output=True, text=True)
            subprocess.run("git branch -M main", shell=True, capture_output=True, text=True)

        res_br = subprocess.run("git branch --show-current", shell=True, capture_output=True, text=True)
        active_branch = res_br.stdout.strip() or "main"

        # Helper: compute dependency waves
        def get_execution_waves(subtasks_list: list) -> list[list[dict]]:
            dependencies = {}
            for st in subtasks_list:
                st_id = st["id"]
                depends = st.get("depends_on", [])
                if isinstance(depends, list):
                    dependencies[st_id] = set(str(d) for d in depends if str(d) in subtask_map)
                else:
                    dependencies[st_id] = set()

            waves_list = []
            completed = set()
            remaining = list(subtasks_list)
            while remaining:
                wave = [st for st in remaining if dependencies[st["id"]].issubset(completed)]
                if not wave:
                    wave = [remaining[0]]
                waves_list.append(wave)
                for st in wave:
                    completed.add(st["id"])
                    remaining.remove(st)
            return waves_list

        waves = get_execution_waves(subtasks)
        results = {}
        all_conflicts = []
        execution_warnings = []
        subtask_files_written = {}
        all_subtask_writes = {}

        for wave_idx, wave in enumerate(waves):
            # Set up worktrees for this wave
            for subtask in wave:
                subtask_id = subtask["id"]
                worktree_dir = os.path.abspath(os.path.join("..", f"codehive-worker-{subtask_id}"))

                # Remove any leftover worktree/branch from a previous crashed run.
                # git worktree remove unregisters the worktree from git's registry,
                # but it does NOT delete the directory if it wasn't a registered worktree.
                # We must shutil.rmtree the directory too, otherwise git worktree add
                # will fail with "already exists" when a plain dir is left over.
                subprocess.run(f"git worktree remove --force {worktree_dir}", shell=True, capture_output=True, text=True)
                subprocess.run(f"git branch -D task/{subtask_id}", shell=True, capture_output=True, text=True)
                if os.path.exists(worktree_dir):
                    # Safety guard: only delete the directory if git no longer considers
                    # it a registered worktree. This prevents shutil.rmtree from silently
                    # destroying an active worktree that git worktree remove failed to
                    # unregister (e.g. due to a lock or concurrent run).
                    wt_check = subprocess.run(
                        "git worktree list --porcelain",
                        shell=True, capture_output=True, text=True
                    )
                    registered_paths = [
                        line.split(" ", 1)[1].strip()
                        for line in wt_check.stdout.splitlines()
                        if line.startswith("worktree ")
                    ]
                    norm_wt = os.path.normcase(os.path.abspath(worktree_dir))
                    if not any(os.path.normcase(os.path.abspath(p)) == norm_wt for p in registered_paths):
                        shutil.rmtree(worktree_dir, ignore_errors=True)
                    else:
                        print(f"\n[Orchestrator] WARNING: {worktree_dir} is still a registered git worktree — skipping rmtree to avoid data loss.")

                res_wt = subprocess.run(
                    f"git worktree add {worktree_dir} -b task/{subtask_id}",
                    shell=True, capture_output=True, text=True
                )
                if res_wt.returncode != 0:
                    print(f"\n[Orchestrator] ERROR: git worktree add failed for Worker-{subtask_id}: {res_wt.stderr.strip()}")
                else:
                    # INSTRUMENTATION: list files inside the worktree directory right after creation
                    wt_ls = subprocess.run("dir", shell=True, capture_output=True, text=True, cwd=worktree_dir)
                    print(f"\n[Orchestrator] Files in worktree {worktree_dir} at creation:\n{wt_ls.stdout}")

            # Build worker port note (distinct port per worker to avoid collisions)
            def make_worker(subtask, wave_idx=wave_idx):
                subtask_id = subtask["id"]
                worktree_dir = os.path.abspath(os.path.join("..", f"codehive-worker-{subtask_id}"))
                worker_port = 9000 + (100 * wave_idx) + int(subtask_id)
                port_note = (
                    f"NOTE: For any web servers / APIs, you MUST run them on port {worker_port} "
                    f"(to avoid port conflicts with other parallel workers or the main server).\n\n"
                )

                # Build dependency context
                dep_context = ""
                if subtask.get("depends_on"):
                    written_by_deps = []
                    for dep_id in subtask["depends_on"]:
                        written_by_deps.extend(subtask_files_written.get(str(dep_id), []))
                    if written_by_deps:
                        dep_context = (
                            "--- DEPENDENCY FILES ---\n"
                            f"The following files were written by subtasks this depends on: {', '.join(written_by_deps)}.\n"
                            "You MUST call read_file() on each of these before writing code that imports or calls them.\n"
                            "--- END DEPENDENCY FILES ---\n\n"
                        )

                execution_rules = """--- EXECUTION VERIFICATION RULES ---
Writing code is NOT enough. Before finishing your subtask, you MUST actually RUN what you wrote and observe real output.

- Standalone script/function: execute it (e.g. `python script.py`) and show the real output.
- Web API/server (Flask, FastAPI, etc.): start it in the BACKGROUND on your assigned port, send real requests to endpoints via `curl` or Python requests, confirm real responses, THEN stop the server process before finishing.
- Test file (pytest/unittest): RUN the test suite (e.g. `python -m pytest <file>`) and report real pass/fail results.
- Non-executable content (README, config, static assets): existing syntax/sanity checks are sufficient.
After testing, you MUST stop any server process you started, whether the test succeeded or failed.
--- END EXECUTION VERIFICATION RULES ---

"""
                # Wrap tools to execute relative to the worktree path
                worker_tools = []
                for tool in self.tools:
                    if tool.__name__ == "write_file":
                        def wrapped_write(path: str, content: str, wpath=worktree_dir) -> str:
                            abs_path = os.path.normpath(os.path.join(wpath, path))
                            if not abs_path.startswith(os.path.abspath(wpath)):
                                return "ERROR: Path traversal detected."
                            
                            # Self-healing double-escaped content
                            if (path.endswith(".py") or path.endswith(".md")) and "\n" not in content and "\\n" in content:
                                content = content.replace("\\n", "\n").replace("\\t", "\t").replace('\\"', '"').replace("\\'", "'")
                                
                            return tools.write_file(abs_path, content)
                        wrapped_write.__name__ = "write_file"
                        wrapped_write.__doc__ = tools.write_file.__doc__
                        worker_tools.append(wrapped_write)
                    elif tool.__name__ == "read_file":
                        def wrapped_read(path: str, wpath=worktree_dir) -> str:
                            abs_path = os.path.normpath(os.path.join(wpath, path))
                            if not abs_path.startswith(os.path.abspath(wpath)):
                                return "ERROR: Path traversal detected."
                            return tools.read_file(abs_path)
                        wrapped_read.__name__ = "read_file"
                        wrapped_read.__doc__ = tools.read_file.__doc__
                        worker_tools.append(wrapped_read)
                    elif tool.__name__ == "run_bash":
                        def wrapped_bash(command: str, wpath=worktree_dir) -> str:
                            return tools.run_bash(command, cwd=wpath)
                        wrapped_bash.__name__ = "run_bash"
                        wrapped_bash.__doc__ = tools.run_bash.__doc__
                        worker_tools.append(wrapped_bash)
                    else:
                        worker_tools.append(tool)

                # Build conversation-history context for the worker.
                # history is the prior turns from the user session (same list passed to
                # run_workers from the WebSocket / server layer). It gives workers
                # awareness of what was already discussed or built earlier in the session.
                history_ctx = ""
                if history:
                    history_ctx = "--- CONVERSATION HISTORY ---\n"
                    for turn in history:
                        role_label = "User" if turn.get("role") == "user" else "Assistant (CodeHive)"
                        history_ctx += f"{role_label}: {turn.get('content', '')}\n\n"
                    history_ctx += "--- END OF CONVERSATION HISTORY ---\n\n"

                agent = Agent(
                    name=f"Worker-{subtask_id}",
                    role=subtask["title"],
                    system_instruction=(
                        f"You are a senior developer agent working on subtask '{subtask['title']}'.\n\n"
                        f"{history_ctx}"
                        f"{port_note}"
                        f"{dep_context}"
                        f"{execution_rules}"
                        f"Instructions:\n{subtask['instructions']}\n\n"
                        "CRITICAL TOOL CALLING FORMAT RULES:\n"
                        "- When calling a function, your JSON arguments must be properly escaped.\n"
                        "- Multi-line strings in JSON parameters (like 'content') MUST escape all newlines as '\\n' and quotes as '\\\"'.\n"
                        "- Never output raw newlines inside JSON argument strings. Keep the entire JSON argument block on a single line if possible.\n"
                        "- Do not add spaces or extra characters inside the '<function=...>' tag.\n\n"
                        "MANDATORY COMPLETION REQUIREMENT:\n"
                        "- You MUST call write_file for EVERY file listed in your instructions. Do NOT describe what you would write — CALL the tool and write it NOW.\n"
                        "- A text-only response that does not call write_file is WRONG and means your subtask is INCOMPLETE.\n"
                        "- Only after all required write_file calls are done should you output a plain-text summary.\n"
                        "- Do not call any tools after your final summary."
                    ),
                    providers=self.providers,
                    tools=worker_tools,
                    on_tool_call=on_tool_call
                )
                return subtask_id, agent

            # Launch all workers in this wave concurrently
            wave_futures = []
            with ThreadPoolExecutor(max_workers=max(1, len(wave))) as executor:
                agents_in_wave = [make_worker(st) for st in wave]
                for subtask_id, agent in agents_in_wave:
                    st_dict = subtask_map[subtask_id]
                    # History context is already embedded in the agent's system_instruction;
                    # Agent.run() only takes the immediate instructions string.
                    future = loop.run_in_executor(executor, agent.run, st_dict["instructions"])
                    wave_futures.append((subtask_id, future))

                wave_results = {}
                wave_writes = {}
                wave_tool_calls = {}
                for subtask_id, future in wave_futures:
                    try:
                        text, writes, tool_calls = await future
                    except Exception as e:
                        error_type = type(e).__name__
                        text = f"ERROR: {error_type}: {e}"
                        writes = []
                        tool_calls = []
                        print(f"\n[Orchestrator] Worker-{subtask_id} failed: {text}")

                    wave_results[subtask_id] = text
                    wave_writes[subtask_id] = writes
                    wave_tool_calls[subtask_id] = tool_calls
                    subtask_files_written[subtask_id] = [os.path.normpath(w["path"]) for w in writes]

                    # Execution verification audit
                    has_python_writes = any(w["path"].endswith(".py") for w in writes)
                    if has_python_writes:
                        has_execution = False
                        for tc in tool_calls:
                            if tc.get("name") == "run_bash":
                                cmd = tc.get("arguments", {}).get("command", "").lower()
                                if any(term in cmd for term in ("python", "pytest", "unittest", "curl", "requests")):
                                    if "py_compile" not in cmd:
                                        has_execution = True
                                        break
                        if not has_execution:
                            py_file = next(w["path"] for w in writes if w["path"].endswith(".py"))
                            execution_warnings.append({
                                "subtask_id": subtask_id,
                                "path": py_file,
                                "message": f"[WARNING] Worker-{subtask_id} wrote code to {py_file} but only syntax checks or no execution runs were observed."
                            })

                    # Post-write syntax check: py_compile every .py file written by this worker
                    import py_compile, tempfile
                    worktree_dir_check = os.path.abspath(os.path.join("..", f"codehive-worker-{subtask_id}"))
                    for w in writes:
                        wpath = w["path"]
                        if not wpath.endswith(".py"):
                            continue
                        abs_wpath = os.path.normpath(os.path.join(worktree_dir_check, wpath)) if not os.path.isabs(wpath) else wpath
                        if not os.path.exists(abs_wpath):
                            continue
                        try:
                            py_compile.compile(abs_wpath, doraise=True)
                        except py_compile.PyCompileError as compile_err:
                            execution_warnings.append({
                                "subtask_id": subtask_id,
                                "path": wpath,
                                "message": f"[SYNTAX ERROR] Worker-{subtask_id} wrote syntactically invalid Python to {wpath}: {compile_err}"
                            })

            all_subtask_writes.update(wave_writes)
            results.update(wave_results)

            # Commit each worktree and merge back to active branch
            for subtask in wave:
                subtask_id = subtask["id"]
                worktree_dir = os.path.abspath(os.path.join("..", f"codehive-worker-{subtask_id}"))

                subprocess.run("git add -A", shell=True, capture_output=True, text=True, cwd=worktree_dir)
                subprocess.run(f'git commit -m "Commit by Worker {subtask_id}"', shell=True, capture_output=True, text=True, cwd=worktree_dir)

                cmd_merge = f"git merge task/{subtask_id} -m \"Merge Worker {subtask_id}\""
                res_merge = subprocess.run(cmd_merge, shell=True, capture_output=True, text=True)

                if res_merge.returncode != 0:
                    # Real git merge conflict — detect conflicted files
                    res_conf = subprocess.run("git diff --name-only --diff-filter=U", shell=True, capture_output=True, text=True)
                    conf_files = [f.strip() for f in res_conf.stdout.splitlines() if f.strip()]

                    for path in conf_files:
                        resolved = False
                        merged_content = None
                        merge_error = None

                        if os.path.exists(path):
                            try:
                                with open(path, "r", encoding="utf-8") as f_conf:
                                    conf_content = f_conf.read()

                                response_text = self._reconcile_conflict(path, conf_content)

                                raw_merged = response_text.strip()
                                if "```" in raw_merged:
                                    match = re.search(r"```(?:\w+)?\s*(.*?)\s*```", raw_merged, re.DOTALL)
                                    merged_content = match.group(1).strip() if match else raw_merged
                                else:
                                    merged_content = raw_merged

                                if path.endswith(".py"):
                                    ast.parse(merged_content)

                                with open(path, "w", encoding="utf-8") as f_out:
                                    f_out.write(merged_content)

                                subprocess.run(f"git add {path}", shell=True, capture_output=True, text=True)
                                resolved = True

                            except Exception as ex:
                                merge_error = str(ex)

                        # Identify winners and losers by comparing subtask write contents with resolved content
                        norm_path = os.path.normpath(path)
                        conflicting_workers = []
                        winners = []
                        losers = []
                        for sid, w_list in all_subtask_writes.items():
                            wrote_file = False
                            matches_merged = False
                            for w in w_list:
                                if os.path.normpath(w["path"]) == norm_path:
                                    wrote_file = True
                                    if w["content"] == merged_content:
                                        matches_merged = True
                            if wrote_file:
                                conflicting_workers.append(sid)
                                if matches_merged:
                                    winners.append(sid)
                                else:
                                    losers.append(sid)

                        all_conflicts.append({
                            "path": path,
                            "workers": conflicting_workers if conflicting_workers else [subtask_id],
                            "winners": winners,
                            "losers": losers,
                            "resolved": resolved,
                            "merged_content": merged_content,
                            "error": merge_error
                        })

                    subprocess.run('git commit -m "Resolved merge conflicts"', shell=True, capture_output=True, text=True)

            # Cleanup worktrees for this wave
            for subtask in wave:
                subtask_id = subtask["id"]
                worktree_dir = os.path.abspath(os.path.join("..", f"codehive-worker-{subtask_id}"))
                subprocess.run(f"git worktree remove --force {worktree_dir}", shell=True, capture_output=True, text=True)
                subprocess.run(f"git branch -D task/{subtask_id}", shell=True, capture_output=True, text=True)

        return results, all_conflicts, execution_warnings
