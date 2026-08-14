import time
import re
import json
import hashlib

class MockFunction:
    def __init__(self, name, arguments):
        self.name = name
        self.arguments = arguments

class MockToolCall:
    def __init__(self, call_id, name, arguments):
        self.id = call_id
        self.type = "function"
        self.function = MockFunction(name, arguments)

class MockMessage:
    def __init__(self, tool_calls, content=""):
        self.role = "assistant"
        self.content = content
        self.tool_calls = tool_calls
        self.function_call = None
        self.refusal = None

class MockChoice:
    def __init__(self, message):
        self.message = message
        self.finish_reason = "tool_calls" if message.tool_calls else "stop"
        self.index = 0

class MockResponse:
    def __init__(self, message):
        self.choices = [MockChoice(message)]
        self.id = "mock_response_123"
        self.model = "llama-3.3-70b-versatile"
        self.object = "chat.completion"

def clean_and_parse_json(s):
    # Try parsing it directly first
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        pass
        
    chars = []
    in_string = False
    escape = False
    for c in s:
        if c == '"' and not escape:
            in_string = not in_string
            chars.append(c)
        elif c == '\\' and in_string:
            escape = not escape
            chars.append(c)
        elif c == '\n' and in_string:
            chars.append('\\n')  # Escape raw newline!
        elif c == '\r' and in_string:
            chars.append('\\r')  # Escape raw carriage return!
        else:
            escape = False
            chars.append(c)
    
    repaired = "".join(chars)
    try:
        return json.loads(repaired)
    except json.JSONDecodeError as e:
        # Fallback regex if repair parser fails
        path_match = re.search(r'"path"\s*:\s*"([^"]+)"', s)
        cmd_match = re.search(r'"command"\s*:\s*"(.*?)"', s, re.DOTALL)
        content_match = re.search(r'"content"\s*:\s*"(.*)"\s*,?\s*"path"', s, re.DOTALL)
        if not content_match:
            content_match = re.search(r'"path"\s*:\s*"[^"]+"\s*,\s*"content"\s*:\s*"(.*)"', s, re.DOTALL)
        
        res = {}
        if path_match:
            res["path"] = path_match.group(1)
        if cmd_match:
            res["command"] = cmd_match.group(1)
        if content_match:
            content_val = content_match.group(1)
            if content_val.endswith('"}') or content_val.endswith('" }'):
                content_val = content_val.rsplit('"', 1)[0]
            res["content"] = content_val
        
        if res:
            return res
        raise e

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
                    # Check if this is a Groq tool call validation error that we can self-heal
                    if type(e).__name__ == "BadRequestError" and hasattr(e, "body") and isinstance(e.body, dict):
                        error_info = e.body.get("error", {})
                        if error_info.get("code") == "tool_use_failed" and error_info.get("failed_generation"):
                            failed_gen = error_info["failed_generation"]
                            print(f"\n[{self.name}] WARNING: Intercepted Groq tool_use_failed error. Attempting self-healing parse...")
                            
                            # Parse failed generation
                            match = re.search(r"<function=(\w+)(?:\s*)>(.*?)</function>", failed_gen, re.DOTALL)
                            if not match:
                                match = re.search(r"<function=(\w+)(?:\s*)>(.*)", failed_gen, re.DOTALL)
                                
                            func_name = None
                            args_str = None
                            
                            if match:
                                func_name = match.group(1)
                                args_str = match.group(2).strip()
                            else:
                                # Fallback: check if the model put the arguments inside the tag itself, e.g. <function=read_file={"path": "user_db.py"}>
                                match_weird = re.search(r"<function=([a-zA-Z0-9_-]+)=(.*?)(?:/?)>", failed_gen, re.DOTALL)
                                if match_weird:
                                    func_name = match_weird.group(1)
                                    args_str = match_weird.group(2).strip()
                                    # Strip trailing </function> if it exists in args_str
                                    if args_str.endswith("</function>"):
                                        args_str = args_str.rsplit("</function>", 1)[0].strip()
                                    elif args_str.endswith(">"):
                                        args_str = args_str[:-1].strip()
                                else:
                                    # Fallback: check for space-separated arguments inside the tag, e.g. <function=read_file {"path": "user_db.py"}>
                                    match_space = re.search(r"<function=([a-zA-Z0-9_-]+)\s+({.*?})(?:/?)>", failed_gen, re.DOTALL)
                                    if match_space:
                                        func_name = match_space.group(1)
                                        args_str = match_space.group(2).strip()
                                        
                            if func_name and args_str:
                                
                                try:
                                    parsed_args = clean_and_parse_json(args_str)
                                    # Construct MockResponse
                                    mock_tc = MockToolCall(
                                        call_id=f"call_heal_{int(time.time())}_{p_idx}",
                                        name=func_name,
                                        arguments=json.dumps(parsed_args)
                                    )
                                    mock_msg = MockMessage(tool_calls=[mock_tc])
                                    mock_resp = MockResponse(message=mock_msg)
                                    print(f"[{self.name}] SUCCESS: Self-healed tool call parser for {func_name}!")
                                    return mock_resp, p_idx, p_name
                                except Exception as pe:
                                    print(f"[{self.name}] FAILED: Self-healing parse failed to parse JSON arguments: {pe}")

                    # Determine if the error is a permanent request/formatting error or a recoverable failure (rate limit, auth, server error, timeout)
                    status_code = getattr(e, "status_code", None)
                    
                    # 400 (Bad Request), 404 (Not Found), and 422 (Unprocessable Entity) are permanent request/formatting errors
                    is_recoverable = status_code not in (400, 404, 422)
                    
                    # If this provider failed with a recoverable error and we have alternatives, fall back immediately with warning
                    if is_recoverable and num_providers > 1 and offset < num_providers - 1:
                        next_idx = (p_idx + 1) % num_providers
                        next_provider = self.providers[next_idx]
                        print(f"\n[{self.name}] WARNING: {p_name} failed (status {status_code or 'error'}). Falling back immediately to {next_provider['name']}...")
                        continue
                    
                    # Otherwise, if it is a permanent request error, or we have run out of alternative providers
                    if not is_recoverable or offset == num_providers - 1:
                        if attempt < max_retries:
                            # If it is a permanent request error, raise it immediately without retrying further
                            if not is_recoverable:
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
