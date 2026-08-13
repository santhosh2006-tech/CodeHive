"""Diagnostic v2: capture stderr from all git commands in orchestrator flow."""
import asyncio
import os
import subprocess
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Monkey-patch subprocess.run to log all calls
_orig_subprocess_run = subprocess.run

def traced_run(args, **kwargs):
    result = _orig_subprocess_run(args, **kwargs)
    cmd_str = args if isinstance(args, str) else ' '.join(args)
    if any(k in cmd_str for k in ('worktree', 'commit', 'merge', 'branch', 'add')):
        print(f'\n[GIT] cmd: {cmd_str!r}')
        if hasattr(result, 'stdout') and result.stdout:
            print(f'      stdout: {result.stdout.strip()!r}')
        if hasattr(result, 'stderr') and result.stderr:
            print(f'      stderr: {result.stderr.strip()!r}')
        print(f'      rc: {result.returncode}')
    return result

subprocess.run = traced_run

from orchestrator import Orchestrator
from agent import Agent

original_run = Agent.run

def mock_run(self_agent, instructions):
    subtask_id = self_agent.name.split('-')[1]
    worktree_dir = os.path.abspath(os.path.join('..', f'codehive-worker-{subtask_id}'))
    path = os.path.join(worktree_dir, f'temp_clean_{subtask_id}.py')
    os.makedirs(worktree_dir, exist_ok=True)
    with open(path, 'w') as f:
        f.write(f'print("hello from {subtask_id}")')
    writes = [{'path': f'temp_clean_{subtask_id}.py',
               'content': f'print("hello from {subtask_id}")',
               'hash': '123'}]
    return 'Done', writes, []

Agent.run = mock_run

orch = Orchestrator(
    providers=[{'name': 'mock', 'client': None, 'model': 'mock'}],
    tools=[]
)
subtasks = [
    {'id': '1', 'title': 'A', 'instructions': '...', 'depends_on': []},
    {'id': '2', 'title': 'B', 'instructions': '...', 'depends_on': []}
]

results, conflicts, warnings = asyncio.run(orch.run_workers(subtasks))
print('\n--- RESULT ---')
print('conflicts:', conflicts)
print('clean_1 on main?', os.path.exists('temp_clean_1.py'))
print('clean_2 on main?', os.path.exists('temp_clean_2.py'))

Agent.run = original_run
subprocess.run = _orig_subprocess_run

# cleanup
subprocess.run('git rm -f temp_clean_1.py temp_clean_2.py', shell=True, capture_output=True)
subprocess.run('git commit -m "Clean up diag v2"', shell=True, capture_output=True)
for f in ('temp_clean_1.py', 'temp_clean_2.py'):
    if os.path.exists(f):
        os.remove(f)
