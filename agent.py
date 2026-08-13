import time
import re
import json
import hashlib

def get_tools_schema(tools_list):
    """Generates OpenAI-style tools schema list from Python functions."""
    schema_map = {
        "read_file": {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "Read the contents of a text file from the filesystem.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "The path to the file to read."}
                    },
                    "required": ["path"]
                }
            }
        },
        "write_file": {
            "type": "function",
            "function": {
                "name": "write_file",
                "description": "Create a new file or overwrite an existing file with content.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "The path of the file to write."},
                        "content": {"type": "string", "description": "The content to write into the file."}
                    },
                    "required": ["path", "content"]
                }
            }
        },
        "list_dir": {
            "type": "function",
            "function": {
                "name": "list_dir",
                "description": "List the files and directories inside a given folder.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "The directory path to list (defaults to current directory)."}
                    }
                }
            }
        },
        "run_bash": {
            "type": "function",
            "function": {
                "name": "run_bash",
                "description": "Run a bash/shell command on the host system and return standard output and error.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {"type": "string", "description": "The command string to execute in the terminal."}
                    },
                    "required": ["command"]
                }
            }
        }
    }
    
    result = []
    for t in tools_list:
        name = t.__name__
        if name in schema_map:
            result.append(schema_map[name])
    return result if result else None

class Agent:
    def __init__(self, name: str, role: str, system_instruction: str, client=None, model: str = None, tools: list = None, max_turns: int = 15, on_tool_call=None, providers: list = None):
        """Initializes a worker agent.
        
        Args:
            name: Human-readable name of the agent (e.g., 'Worker-1').
            role: The specific role/responsibility of the agent.
            system_instruction: System prompt/instructions guiding the agent's behavior.
            client: Backward-compatible single Groq/OpenAI client instance.
            model: Backward-compatible model name.
            tools: List of Python functions to expose as tools.
            max_turns: Safety cap to prevent infinite loops.
            on_tool_call: Optional thread-safe callback(agent_name, tool_name, args, provider_name) for live logging.
            providers: List of provider configurations dicts {"name": ..., "client": ..., "model": ...}
        """
        self.name = name
        self.role = role
        self.system_instruction = system_instruction
        self.tools = tools or []
        self.max_turns = max_turns
        self.on_tool_call = on_tool_call
        self.tool_map = {f.__name__: f for f in self.tools}
        self.tools_schema = get_tools_schema(self.tools)
        
        # Load providers for fallback routing
        if client:
            self.providers = [{
                "name": "mock",
                "client": client,
                "model": model or "llama-3.3-70b-versatile"
            }]
        else:
            self.providers = providers or []

    def _send_message_with_retry(self, messages, active_provider_idx=0):
        """Attempts to send messages using the active provider first, 
        falling back to alternative providers on rate limits (429/503) 
        before sleeping.
        """
        max_retries = 3
        base_backoff = 10
        num_providers = len(self.providers)
        
        if num_providers == 0:
            raise ValueError("No providers configured. Please set GROQ_API_KEY or NVIDIA_API_KEY.")

        for attempt in range(max_retries + 1):
            # Try providers sequentially starting from the active provider index
            for offset in range(num_providers):
                p_idx = (active_provider_idx + offset) % num_providers
                provider = self.providers[p_idx]
                p_name = provider["name"]
                p_client = provider["client"]
                p_model = provider["model"]
                
                try:
                    kwargs = {
                        "model": p_model,
                        "messages": messages
                    }
                    if self.tools_schema:
                        kwargs["tools"] = self.tools_schema
                    
                    # INSTRUMENTATION: print actual tools_schema being sent
                    print(f"\n[{self.name}] API request tools_schema: {self.tools_schema}")
                        
                    response = p_client.chat.completions.create(**kwargs)
                    return response, p_idx, p_name
                    
                except Exception as e:
                    # Determine if the error is a permanent client error or transient/rate-limit
                    status_code = getattr(e, "status_code", None)
                    is_transient = True
                    if status_code in (400, 401, 403, 404, 422):
                        is_transient = False
                    
                    # If this provider failed with a transient error and we have alternatives, fall back immediately
                    if is_transient and num_providers > 1 and offset < num_providers - 1:
                        next_idx = (p_idx + 1) % num_providers
                        next_provider = self.providers[next_idx]
                        print(f"\n[{self.name}] WARNING: {p_name} failed (status {status_code or 'error'}). Falling back immediately to {next_provider['name']}...")
                        continue
                    
                    # If this is the last provider in the chain for this retry attempt, sleep and try again
                    if offset == num_providers - 1:
                        if attempt < max_retries:
                            # If it's a permanent error, raise it immediately without retrying
                            if not is_transient:
                                raise e
                                
                            delay = base_backoff * (2 ** attempt)
                            match = re.search(r"retry_after[\'\"]?:\s*[\'\"]?(\d+)s?[\'\"]?", str(e), re.IGNORECASE)
                            if not match:
                                match = re.search(r"retry[\'\"]?\s*after\s*(\d+)s?", str(e), re.IGNORECASE)
                            if match:
                                try:
                                    delay = int(match.group(1)) + 1
                                except Exception:
                                    pass
                            
                            print(f"\n[{self.name}] WARNING: All providers failed. Retrying in {delay} seconds (attempt {attempt + 1}/{max_retries})...")
                            time.sleep(delay)
                        else:
                            raise e

    def run(self, user_prompt: str) -> tuple[str, list[dict], list[dict]]:
        """Runs the agent's tool-calling loop until completion or max_turns is reached.
        
        Returns:
            A tuple of (result_text, writes, tool_calls_made) where writes is a list of write records
            and tool_calls_made is a list of dicts representing tool calls made.
        """
        writes = []
        tool_calls_made = []
        messages = [
            {"role": "system", "content": self.system_instruction},
            {"role": "user", "content": user_prompt}
        ]
        
        active_provider_idx = 0
        try:
            turns = 1
            while turns < self.max_turns:
                response, active_provider_idx, p_name = self._send_message_with_retry(messages, active_provider_idx)
                assistant_message = response.choices[0].message
                
                # Append assistant message dict representation to keep history clean
                msg_dict = {"role": "assistant"}
                if assistant_message.content:
                    msg_dict["content"] = assistant_message.content
                if assistant_message.tool_calls:
                    msg_dict["tool_calls"] = assistant_message.tool_calls
                messages.append(msg_dict)
                
                tool_calls = assistant_message.tool_calls
                if not tool_calls:
                    return assistant_message.content or "", writes, tool_calls_made

                # Process all tool calls concurrently requested in this turn
                for call in tool_calls:
                    name = call.function.name
                    call_id = call.id
                    
                    try:
                        args = json.loads(call.function.arguments) if call.function.arguments else {}
                    except Exception:
                        args = {}

                    # Track the tool call made
                    tool_calls_made.append({"name": name, "arguments": args})

                    if self.on_tool_call:
                        self.on_tool_call(self.name, name, args, p_name)

                    if name in self.tool_map:
                        try:
                            kwargs = dict(args)
                            result = self.tool_map[name](**kwargs)
                            if name == "write_file" and not result.startswith("ERROR"):
                                content = kwargs.get("content", "")
                                path = kwargs.get("path", "")
                                content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
                                writes.append({
                                    "path": path,
                                    "content": content,
                                    "hash": content_hash,
                                    "timestamp": time.time()
                                })
                        except Exception as e:
                            result = f"ERROR: {str(e)}"
                    else:
                        result = f"ERROR: Tool {name} not found."

                    messages.append({
                        "role": "tool",
                        "tool_call_id": call_id,
                        "name": name,
                        "content": str(result)
                    })

                turns += 1

            return f"ERROR: Reached max turns cap of {self.max_turns} without finishing.", writes, tool_calls_made

        except Exception as e:
            status_code = getattr(e, "status_code", None)
            if status_code in (429, 503) or "rate limit" in str(e).lower() or "quota" in str(e).lower() or "over_limit" in str(e).lower():
                return "ERROR: Rate limited or model unavailable, subtask incomplete.", writes, tool_calls_made
            raise e
