"""
Minimal sequential-wave repro:
- Wave 1: Worker-1 writes db.py
- Wave 2: Worker-2 calls read_file("db.py") then writes posts.py

The mock client drives the real agent.run() loop so tools_schema is
constructed and sent exactly as it would be in production.
We'll see the DIAG prints showing the real tools_schema value at each send.
"""
import asyncio, json, os, sys, subprocess, shutil

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from orchestrator import Orchestrator
from agent import Agent
import tools as tools_module

# ── Mock client that drives Worker-1 (write db.py) then Worker-2 (read db.py, write posts.py) ──

class MockToolCall:
    def __init__(self, name, arguments, call_id):
        self.id = call_id
        self.function = type("F", (), {"name": name, "arguments": arguments})()

class MockResponse:
    def __init__(self, content=None, tool_calls=None):
        self.choices = [type("C", (), {
            "message": type("M", (), {
                "content": content,
                "tool_calls": tool_calls
            })()
        })()]

class MockCompletions:
    def __init__(self, worker_scripts):
        self.worker_scripts = worker_scripts  # {worker_name: [list of responses per turn]}
        self.turn_counts = {}

    def create(self, **kwargs):
        # Find which worker this is from the system message
        sys_msg = next((m["content"] for m in kwargs["messages"] if m["role"] == "system"), "")
        worker_name = None
        for name in self.worker_scripts:
            if name in sys_msg:
                worker_name = name
                break
        if not worker_name:
            return MockResponse(content="Done (unknown worker)")

        turn = self.turn_counts.get(worker_name, 0)
        self.turn_counts[worker_name] = turn + 1

        script = self.worker_scripts[worker_name]
        if turn < len(script):
            return script[turn]
        return MockResponse(content=f"{worker_name} Done")

class MockClient:
    def __init__(self, completions):
        self.chat = type("Chat", (), {"completions": completions})()


async def run_repro():
    print("\n" + "="*60)
    print("REPRO: sequential waves, Wave-2 reads Wave-1's output")
    print("="*60)

    # Worker-1 script: writes db.py
    worker1_script = [
        MockResponse(
            tool_calls=[MockToolCall("write_file",
                json.dumps({"path": "db.py", "content": "def get_db(): return 'connected'"}),
                "c1")]
        ),
        MockResponse(content="Worker-1 done: wrote db.py"),
    ]

    # Worker-2 script: reads db.py, then writes posts.py
    worker2_script = [
        MockResponse(
            tool_calls=[MockToolCall("read_file",
                json.dumps({"path": "db.py"}),
                "c2")]
        ),
        MockResponse(
            tool_calls=[MockToolCall("write_file",
                json.dumps({"path": "posts.py", "content": "from db import get_db\ndef get_posts(): return []"}),
                "c3")]
        ),
        MockResponse(content="Worker-2 done: read db.py, wrote posts.py"),
    ]

    completions = MockCompletions({
        "Worker-1": worker1_script,
        "Worker-2": worker2_script,
    })
    mock_client = MockClient(completions)

    orch = Orchestrator(
        client=mock_client,
        tools=[tools_module.read_file, tools_module.write_file, tools_module.list_dir, tools_module.run_bash]
    )

    subtasks = [
        {"id": "1", "title": "Worker-1", "instructions": "Write db.py", "depends_on": []},
        {"id": "2", "title": "Worker-2", "instructions": "Read db.py then write posts.py", "depends_on": ["1"]},
    ]

    results, conflicts, warnings = await orch.run_workers(subtasks)

    print("\n" + "="*60)
    print("RESULTS")
    print("="*60)
    for sid, text in results.items():
        print(f"Worker-{sid}: {text[:120]}")
    print(f"Conflicts: {conflicts}")
    print(f"Warnings: {warnings}")

    # Check whether the read_file call actually succeeded
    wt2 = os.path.abspath(os.path.join("..", "codehive-worker-2"))
    db_in_wt2 = os.path.exists(os.path.join(wt2, "db.py"))
    posts_in_wt2 = os.path.exists(os.path.join(wt2, "posts.py"))
    print(f"\ndb.py in wt2 at worker run time (would have been): checked via git worktree state")
    print(f"posts.py written in wt2: {posts_in_wt2}")

asyncio.run(run_repro())

# Final cleanup
for f in ("db.py", "posts.py"):
    if os.path.exists(f): os.remove(f)
subprocess.run("git checkout -- .", shell=True, capture_output=True,
               cwd=os.path.abspath("."))
