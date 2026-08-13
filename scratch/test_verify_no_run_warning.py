import os
import sys
import asyncio
from dotenv import load_dotenv
load_dotenv()

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from providers import get_providers
from orchestrator import Orchestrator
from agent import Agent

async def main():
    providers = get_providers()
    orchestrator = Orchestrator(providers=providers, tools=[])
    
    # Mock Agent.run to simulate a worker writing a python file but only running py_compile
    original_run = Agent.run
    def mock_run(self_agent, instructions, history=None):
        subtask_id = self_agent.name.split("-")[1]
        worktree_dir = os.path.abspath(os.path.join("..", f"codehive-worker-{subtask_id}"))
        os.makedirs(worktree_dir, exist_ok=True)
        
        path = os.path.join(worktree_dir, "app.py")
        with open(path, "w", encoding="utf-8") as f:
            f.write("print('hello')")
            
        writes = [{"path": "app.py", "content": "print('hello')", "hash": "123"}]
        # Tool call contains run_bash but only with py_compile (syntax check)
        tool_calls = [
            {"name": "write_file", "arguments": {"path": "app.py", "content": "print('hello')"}},
            {"name": "run_bash", "arguments": {"command": "python -m py_compile app.py"}}
        ]
        return "Finished task successfully.", writes, tool_calls
        
    Agent.run = mock_run
    
    try:
        subtasks = [
            {"id": "1", "title": "Write Python App", "instructions": "Write app.py.", "depends_on": []}
        ]
        
        # Commit base files to git so we can run clean
        with open("app.py", "w") as f:
            f.write("")
        import subprocess
        subprocess.run("git add app.py", shell=True, capture_output=True)
        subprocess.run('git commit -m "Base for warning test"', shell=True, capture_output=True)
        
        results, conflicts, execution_warnings = await orchestrator.run_workers(subtasks)
        
        print("\n=== EXECUTION AUDIT OUTPUT ===")
        print("Execution Warnings:", execution_warnings)
        print("===============================")
        
    finally:
        import subprocess
        subprocess.run("git rm -f app.py", shell=True, capture_output=True)
        subprocess.run('git commit -m "Clean up warning test"', shell=True, capture_output=True)
        if os.path.exists("app.py"):
            os.remove("app.py")
        Agent.run = original_run

if __name__ == "__main__":
    asyncio.run(main())
