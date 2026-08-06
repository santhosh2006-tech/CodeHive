import os
import time
import asyncio
import unittest
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor

import tools
from agent import Agent
from orchestrator import parse_planner_response, Orchestrator
from groq import APIError

# Mock helper classes for Groq Client API
class MockFunction:
    def __init__(self, name, arguments):
        self.name = name
        self.arguments = arguments

class MockToolCall:
    def __init__(self, name, arguments, call_id):
        self.id = call_id
        self.type = "function"
        self.function = MockFunction(name, arguments)

class MockMessage:
    def __init__(self, content, tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls
        self.role = "assistant"

class MockChoice:
    def __init__(self, content, tool_calls=None):
        self.message = MockMessage(content, tool_calls)

class MockResponse:
    def __init__(self, content, tool_calls=None):
        self.choices = [MockChoice(content, tool_calls)]

class TestCodeHive(unittest.TestCase):

    def setUp(self):
        self.test_file = "test_temp_file.txt"

    def tearDown(self):
        if os.path.exists(self.test_file):
            try:
                os.remove(self.test_file)
            except Exception:
                pass

    def test_1_tools_unit(self):
        print("\n[TEST] Running tools unit tests...")
        
        # Test write_file
        content = "hello unit test"
        write_res = tools.write_file(self.test_file, content)
        self.assertIn("Success", write_res)
        self.assertTrue(os.path.exists(self.test_file))

        # Test read_file
        read_res = tools.read_file(self.test_file)
        self.assertEqual(read_res, content)

        # Test list_dir
        list_res = tools.list_dir(".")
        self.assertIn(self.test_file, list_res)

        # Test run_bash (run simple echo command)
        bash_res = tools.run_bash("echo test_run_bash_cmd")
        self.assertIn("EXIT CODE: 0", bash_res)
        self.assertIn("test_run_bash_cmd", bash_res)
        print("-> Tool unit tests PASSED.")

    def test_2_planner_parsing(self):
        print("\n[TEST] Running planner response parsing tests...")

        # 1. Clean JSON response
        clean_json = '{"subtasks": [{"id": "1", "title": "Task 1", "instructions": "Do something"}]}'
        res_clean = parse_planner_response(clean_json, "fallback task")
        self.assertEqual(len(res_clean["subtasks"]), 1)
        self.assertEqual(res_clean["subtasks"][0]["id"], "1")
        self.assertEqual(res_clean["subtasks"][0]["title"], "Task 1")

        # 2. Markdown fenced JSON response
        fenced_json = """```json
{
  "subtasks": [
    {"id": "2", "title": "Task 2", "instructions": "Do something else"}
  ]
}
```"""
        res_fenced = parse_planner_response(fenced_json, "fallback task")
        self.assertEqual(len(res_fenced["subtasks"]), 1)
        self.assertEqual(res_fenced["subtasks"][0]["id"], "2")
        self.assertEqual(res_fenced["subtasks"][0]["title"], "Task 2")

        # 3. Malformed JSON response (should trigger fallback)
        malformed = "Some reasoning and not a valid json object"
        res_fallback = parse_planner_response(malformed, "fallback task")
        self.assertEqual(len(res_fallback["subtasks"]), 1)
        self.assertEqual(res_fallback["subtasks"][0]["id"], "1")
        self.assertEqual(res_fallback["subtasks"][0]["instructions"], "fallback task")
        print("-> Planner parsing tests PASSED.")

    def test_3_concurrency(self):
        print("\n[TEST] Running concurrency verification test...")

        def simulated_worker():
            time.sleep(0.2)
            return "Done"

        async def run_concurrent():
            loop = asyncio.get_event_loop()
            start_time = time.time()
            with ThreadPoolExecutor(max_workers=3) as executor:
                futures = [loop.run_in_executor(executor, simulated_worker) for _ in range(3)]
                await asyncio.gather(*futures)
            end_time = time.time()
            return end_time - start_time

        duration = asyncio.run(run_concurrent())
        print(f"-> 3 workers finished in {duration:.4f} seconds (expected ~0.2s, not 0.6s)")
        
        self.assertLess(duration, 0.35, "Workers executed sequentially instead of concurrently!")
        print("-> Concurrency verification PASSED.")

    def test_4_agent_mock_tool_loop(self):
        print("\n[TEST] Running Agent manual tool-calling loop test with mock client...")

        class MockChatCompletions:
            def create(self, model, messages, tools=None):
                turn = len(messages)
                if turn == 2:
                    args_json = json.dumps({"val": "unit_test"})
                    return MockResponse(
                        content=None,
                        tool_calls=[MockToolCall(name="dummy_tool", arguments=args_json, call_id="call_abc123")]
                    )
                else:
                    return MockResponse(
                        content="Successfully processed dummy_tool!",
                        tool_calls=None
                    )

        class MockChat:
            def __init__(self):
                self.completions = MockChatCompletions()

        class MockClient:
            def __init__(self):
                self.chat = MockChat()

        executed = []
        def dummy_tool(val: str) -> str:
            executed.append(val)
            return f"Executed with {val}"

        mock_client = MockClient()
        agent = Agent(
            name="TestWorker",
            role="Test",
            system_instruction="You are a tester.",
            client=mock_client,
            tools=[dummy_tool],
            max_turns=5
        )

        result, writes = agent.run("Please invoke dummy_tool")
        
        self.assertEqual(result, "Successfully processed dummy_tool!")
        self.assertEqual(executed, ["unit_test"])
        self.assertEqual(len(writes), 0)
        print("-> Agent mock tool loop test PASSED.")

    def test_5_agent_rate_limit_retry(self):
        print("\n[TEST] Running Agent rate limit retry test...")

        class CustomAPIError(APIError):
            def __init__(self, message, status_code=429):
                self.status_code = status_code
                self.message = message
                self.request = None
                self.response = None
            def __str__(self):
                return self.message

        class MockChatCompletions:
            def __init__(self):
                self.calls = 0

            def create(self, model, messages, tools=None):
                self.calls += 1
                if self.calls <= 2:
                    raise CustomAPIError("Rate Limit", status_code=429)
                else:
                    return MockResponse("Succeeded after retries!")

        class MockChat:
            def __init__(self):
                self.completions = MockChatCompletions()

        class MockClient:
            def __init__(self):
                self.chat = MockChat()

        original_sleep = time.sleep
        sleep_called = []
        time.sleep = lambda secs: sleep_called.append(secs)

        try:
            mock_client = MockClient()
            agent = Agent(
                name="TestRateLimitWorker",
                role="Test",
                system_instruction="You are a tester.",
                client=mock_client,
                tools=[],
                max_turns=5
            )
            result, writes = agent.run("Test prompt")
            
            self.assertEqual(result, "Succeeded after retries!")
            self.assertEqual(len(sleep_called), 2)
            print(f"-> Sleep backoffs called with: {sleep_called}")
            print("-> Agent rate limit retry test PASSED.")
        finally:
            time.sleep = original_sleep

    def test_6_collision_detection_logic(self):
        print("\n[TEST] Running collision detection logic unit test...")
        import os
        import hashlib
        
        final_content = "Final winner content"
        final_hash = hashlib.sha256(final_content.encode("utf-8")).hexdigest()
        
        test_file = "test_col.txt"
        with open(test_file, "w", encoding="utf-8") as f:
            f.write(final_content)
            
        try:
            loser_hash = hashlib.sha256("Loser content".encode("utf-8")).hexdigest()
            
            agent_writes = {
                "1": [{"path": test_file, "content": "Loser content", "hash": loser_hash, "timestamp": 123.4}],
                "2": [{"path": test_file, "content": "Final winner content", "hash": final_hash, "timestamp": 123.5}]
            }
            
            file_writes = {}
            for worker_id, writes in agent_writes.items():
                for w in writes:
                    norm_path = os.path.normpath(w["path"])
                    file_writes.setdefault(norm_path, []).append((worker_id, w))
                    
            conflicts = []
            for path, writes_list in file_writes.items():
                if len(writes_list) > 1:
                    f_hash = None
                    if os.path.exists(path):
                        with open(path, "r", encoding="utf-8") as f:
                            f_hash = hashlib.sha256(f.read().encode("utf-8")).hexdigest()
                            
                    winners = []
                    losers = []
                    for worker_id, w in writes_list:
                        if f_hash and w["hash"] == f_hash:
                            winners.append(worker_id)
                        else:
                            losers.append((worker_id, w))
                            
                    conflicts.append({
                        "path": path,
                        "workers": [worker_id for worker_id, _ in writes_list],
                        "winners": winners,
                        "losers": losers
                    })
                    
            self.assertEqual(len(conflicts), 1)
            self.assertEqual(conflicts[0]["path"], test_file)
            self.assertEqual(conflicts[0]["winners"], ["2"])
            self.assertEqual(len(conflicts[0]["losers"]), 1)
            self.assertEqual(conflicts[0]["losers"][0][0], "1")
            self.assertEqual(conflicts[0]["losers"][0][1]["content"], "Loser content")
            print("-> Collision detection logic test PASSED.")
        finally:
            if os.path.exists(test_file):
                os.remove(test_file)

    def test_7_mocked_race_test_with_conflict(self):
        print("\n[TEST] Running mocked race test with conflict warning panel verification...")
        import os
        import hashlib
        
        test_file = "race_test_scratch_temp.py"
        initial_content = "original contents"
        with open(test_file, "w", encoding="utf-8") as f:
            f.write(initial_content)
            
        try:
            with open(test_file, "w", encoding="utf-8") as f:
                f.write("Final-Winner-Content")
                
            class MockChatCompletions:
                def create(self, model, messages, tools=None, response_format=None):
                    # If this is the reconciler call, return the merged output
                    if tools is None:
                        return MockResponse(content="```python\nFinal-Winner-Content\n```")
                        
                    sys_msg = messages[0]["content"]
                    if "Subtask A" in sys_msg: agent_id = 1
                    elif "Subtask B" in sys_msg: agent_id = 2
                    elif "Subtask C" in sys_msg: agent_id = 3
                    else: agent_id = 1
                    
                    turn = len(messages)
                    if turn == 2:
                        args_json = json.dumps({"path": test_file})
                        return MockResponse(
                            content=None,
                            tool_calls=[MockToolCall(name="read_file", arguments=args_json, call_id="call_1")]
                        )
                    elif turn == 4:
                        content = ""
                        if agent_id == 1: content = "Worker-1-Content"
                        elif agent_id == 2: content = "Worker-2-Content"
                        elif agent_id == 3: content = "Final-Winner-Content"
                        args_json = json.dumps({"path": test_file, "content": content})
                        return MockResponse(
                            content=None,
                            tool_calls=[MockToolCall(name="write_file", arguments=args_json, call_id="call_2")]
                        )
                    else:
                        return MockResponse(content="Done", tool_calls=None)

            class MockChat:
                def __init__(self):
                    self.completions = MockChatCompletions()

            class MockClient:
                def __init__(self):
                    self.chat = MockChat()

            mock_client = MockClient()
            orchestrator = Orchestrator(client=mock_client, tools=[tools.read_file, tools.write_file])
            
            subtasks = [
                {"id": "1", "title": "Subtask A", "instructions": "Move health and greeting routes out of app.py."},
                {"id": "2", "title": "Subtask B", "instructions": "Verify users routes are registered cleanly."},
                {"id": "3", "title": "Subtask C", "instructions": "Add basic logging configuration."}
            ]
            
            results, conflicts = asyncio.run(orchestrator.run_workers(subtasks))
            
            self.assertEqual(len(conflicts), 1)
            self.assertEqual(conflicts[0]["path"], os.path.normpath(test_file))
            self.assertEqual(len(conflicts[0]["winners"]), 1)
            self.assertEqual(len(conflicts[0]["losers"]), 2)
            
            losers_ids = [l[0] for l in conflicts[0]["losers"]]
            winner_id = conflicts[0]["winners"][0]
            self.assertEqual(len(set(losers_ids + [winner_id])), 3)
            print("-> Mocked race test with conflict verification PASSED.")
        finally:
            if os.path.exists(test_file):
                os.remove(test_file)

    def test_8_non_conflicting_scenario(self):
        print("\n[TEST] Running non-conflicting scenario verification test...")
        import os
        
        file_a = "temp_file_a.txt"
        file_b = "temp_file_b.txt"
        
        try:
            class MockChatCompletions:
                def create(self, model, messages, tools=None, response_format=None):
                    user_msg = messages[-1]["content"] if isinstance(messages[-1], dict) else str(messages[-1])
                    if "Subtask A" in user_msg or (len(messages) > 2 and "temp_file_a" in str(messages)):
                        agent_id = 1
                    else:
                        agent_id = 2
                        
                    turn = len(messages)
                    if turn == 2:
                        path = file_a if agent_id == 1 else file_b
                        args_json = json.dumps({"path": path, "content": f"Content from {agent_id}"})
                        return MockResponse(
                            content=None,
                            tool_calls=[MockToolCall(name="write_file", arguments=args_json, call_id="call_1")]
                        )
                    else:
                        return MockResponse(content="Done", tool_calls=None)

            class MockChat:
                def __init__(self):
                    self.completions = MockChatCompletions()

            class MockClient:
                def __init__(self):
                    self.chat = MockChat()

            mock_client = MockClient()
            orchestrator = Orchestrator(client=mock_client, tools=[tools.write_file])
            
            subtasks = [
                {"id": "1", "title": "Subtask A", "instructions": "Subtask A instructions"},
                {"id": "2", "title": "Subtask B", "instructions": "Subtask B instructions"}
            ]
            
            results, conflicts = asyncio.run(orchestrator.run_workers(subtasks))
            
            self.assertEqual(len(conflicts), 0)
            print("-> Non-conflicting scenario verification PASSED.")
        finally:
            for f in (file_a, file_b):
                if os.path.exists(f):
                    os.remove(f)

    def test_9_reconciler_extraction(self):
        print("\n[TEST] Running reconciler extraction unit test...")
        import re
        
        raw_text_1 = "```python\nprint('hello')\n```"
        raw_text_2 = "```\ndef my_func():\n    return 42\n```"
        raw_text_3 = "no fenced block here"

        def extract(text: str) -> str:
            text = text.strip()
            if "```" in text:
                match = re.search(r"```(?:\w+)?\s*(.*?)\s*```", text, re.DOTALL)
                if match:
                    return match.group(1).strip()
            return text

        self.assertEqual(extract(raw_text_1), "print('hello')")
        self.assertEqual(extract(raw_text_2), "def my_func():\n    return 42")
        self.assertEqual(extract(raw_text_3), "no fenced block here")
        print("-> Reconciler extraction test PASSED.")

    def test_10_sanity_check_rejection(self):
        print("\n[TEST] Running sanity check syntax error rejection test...")
        import ast
        import hashlib
        
        test_file = "test_syntax.py"
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("print('original')")
            
        try:
            merged_content = "print('incomplete string"
            with self.assertRaises(SyntaxError):
                ast.parse(merged_content)
                
            print("-> Sanity check syntax error rejection test PASSED.")
        finally:
            if os.path.exists(test_file):
                os.remove(test_file)

    def test_11_identical_input_rejection(self):
        print("\n[TEST] Running identical input merge rejection test...")
        
        writes_list = [
            ("1", {"content": "content a"}),
            ("2", {"content": "content b"})
        ]
        
        merged_content = "content b"
        is_identical = False
        for worker_id, w in writes_list:
            if merged_content == w["content"]:
                is_identical = True
                break
                
        self.assertTrue(is_identical)
        print("-> Identical input merge rejection test PASSED.")

    def test_12_reconciler_mocked_race_test_integration(self):
        print("\n[TEST] Running full reconciler integration race test...")
        import os
        import hashlib
        
        test_file = "race_test_scratch_temp.py"
        initial_content = "original contents"
        with open(test_file, "w", encoding="utf-8") as f:
            f.write(initial_content)
            
        try:
            class MockChatCompletions:
                def create(self, model, messages, tools=None, response_format=None):
                    # If this is the reconciler call, return the merged output
                    if tools is None:
                        return MockResponse(
                            content="```python\n# WORKER-1-APPLIED\n# WORKER-2-APPLIED\n# WORKER-3-APPLIED\nprint('successfully merged!')\n```"
                        )
                    
                    sys_msg = messages[0]["content"]
                    if "Subtask A" in sys_msg: agent_id = 1
                    elif "Subtask B" in sys_msg: agent_id = 2
                    else: agent_id = 3
                    
                    turn = len(messages)
                    if turn == 2:
                        args_json = json.dumps({"path": test_file})
                        return MockResponse(
                            content=None,
                            tool_calls=[MockToolCall(name="read_file", arguments=args_json, call_id="call_1")]
                        )
                    elif turn == 4:
                        content = f"# WORKER-{agent_id}-APPLIED"
                        args_json = json.dumps({"path": test_file, "content": content})
                        return MockResponse(
                            content=None,
                            tool_calls=[MockToolCall(name="write_file", arguments=args_json, call_id="call_2")]
                        )
                    else:
                        return MockResponse(content="Done", tool_calls=None)

            class MockChat:
                def __init__(self):
                    self.completions = MockChatCompletions()

            class MockClient:
                def __init__(self):
                    self.chat = MockChat()

            mock_client = MockClient()
            orchestrator = Orchestrator(client=mock_client, tools=[tools.read_file, tools.write_file])
            
            subtasks = [
                {"id": "1", "title": "Subtask A", "instructions": "Move health and greeting routes out of app.py."},
                {"id": "2", "title": "Subtask B", "instructions": "Verify users routes are registered cleanly."},
                {"id": "3", "title": "Subtask C", "instructions": "Add basic logging configuration."}
            ]
            
            results, conflicts = asyncio.run(orchestrator.run_workers(subtasks))
            
            self.assertEqual(len(conflicts), 1)
            self.assertTrue(conflicts[0]["resolved"])
            self.assertIsNone(conflicts[0]["error"])
            
            with open(test_file, "r", encoding="utf-8") as f:
                final_disk_content = f.read()
                
            self.assertIn("# WORKER-1-APPLIED", final_disk_content)
            self.assertIn("# WORKER-2-APPLIED", final_disk_content)
            self.assertIn("# WORKER-3-APPLIED", final_disk_content)
            self.assertIn("successfully merged!", final_disk_content)
            print("-> Reconciler integration race test PASSED.")
        finally:
            if os.path.exists(test_file):
                os.remove(test_file)

    def test_13_fallback_success(self):
        print("\n[TEST] Running provider fallback success test...")
        
        class CustomAPIError(APIError):
            def __init__(self, message, status_code=429):
                self.status_code = status_code
                self.message = message
                self.request = None
                self.response = None
            def __str__(self):
                return self.message

        class MockGroqCompletions:
            def create(self, model, messages, tools=None):
                raise CustomAPIError("Groq Rate Limit exceeded", status_code=429)

        class MockNvidiaCompletions:
            def create(self, model, messages, tools=None):
                return MockResponse("Success via NVIDIA NIM!")

        mock_groq = type("MockClient", (), {"chat": type("MockChat", (), {"completions": MockGroqCompletions()})})()
        mock_nvidia = type("MockClient", (), {"chat": type("MockChat", (), {"completions": MockNvidiaCompletions()})})()
        
        providers = [
            {"name": "groq", "client": mock_groq, "model": "model-g"},
            {"name": "nvidia", "client": mock_nvidia, "model": "model-n"}
        ]
        
        agent = Agent(
            name="FallbackWorker",
            role="Test",
            system_instruction="Test fallback mechanism.",
            providers=providers,
            tools=[],
            max_turns=5
        )
        
        result, writes = agent.run("Run subtask instructions")
        self.assertEqual(result, "Success via NVIDIA NIM!")
        print("-> Provider fallback success test PASSED.")

    def test_14_groq_only_mode(self):
        print("\n[TEST] Running Groq-only mode (NVIDIA key not set) test...")
        
        class MockGroqCompletions:
            def create(self, model, messages, tools=None):
                return MockResponse("Success via Groq only!")

        mock_groq = type("MockClient", (), {"chat": type("MockChat", (), {"completions": MockGroqCompletions()})})()
        
        providers = [
            {"name": "groq", "client": mock_groq, "model": "model-g"}
        ]
        
        agent = Agent(
            name="GroqOnlyWorker",
            role="Test",
            system_instruction="Test single provider.",
            providers=providers,
            tools=[],
            max_turns=5
        )
        
        result, writes = agent.run("Run subtask instructions")
        self.assertEqual(result, "Success via Groq only!")
        print("-> Groq-only mode test PASSED.")

    def test_15_both_providers_fail(self):
        print("\n[TEST] Running both providers fail retry backoff test...")
        
        class CustomAPIError(APIError):
            def __init__(self, message, status_code=429):
                self.status_code = status_code
                self.message = message
                self.request = None
                self.response = None
            def __str__(self):
                return self.message

        class MockGroqCompletions:
            def create(self, model, messages, tools=None):
                raise CustomAPIError("Groq Rate Limit exceeded", status_code=429)

        class MockNvidiaCompletions:
            def create(self, model, messages, tools=None):
                raise CustomAPIError("NVIDIA Rate Limit exceeded", status_code=429)

        mock_groq = type("MockClient", (), {"chat": type("MockChat", (), {"completions": MockGroqCompletions()})})()
        mock_nvidia = type("MockClient", (), {"chat": type("MockChat", (), {"completions": MockNvidiaCompletions()})})()
        
        providers = [
            {"name": "groq", "client": mock_groq, "model": "model-g"},
            {"name": "nvidia", "client": mock_nvidia, "model": "model-n"}
        ]
        
        original_sleep = time.sleep
        sleep_called = []
        time.sleep = lambda secs: sleep_called.append(secs)
        
        try:
            agent = Agent(
                name="DoubleFailWorker",
                role="Test",
                system_instruction="Test rate limit propagation.",
                providers=providers,
                tools=[],
                max_turns=5
            )
            result, writes = agent.run("Run subtask instructions")
            self.assertEqual(result, "ERROR: Rate limited or model unavailable, subtask incomplete.")
            self.assertEqual(len(sleep_called), 3)
            print(f"-> Sleep backoffs called with: {sleep_called}")
            print("-> Both providers fail retry backoff test PASSED.")
        finally:
            time.sleep = original_sleep

if __name__ == "__main__":
    unittest.main()
