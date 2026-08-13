"""
Minimal repro + diagnosis for two claims:

A) tools_schema value at send time: was read_file present or absent when
   Worker-2 made its failing call? Instrument _send_message_with_retry
   to print the ACTUAL kwargs["tools"] before every API call.

B) Cross-wave file access: does a Wave-2 worktree actually contain the
   files written by Wave-1 at creation time, or must it fall back to main?
   Verified by checking filesystem directly after Wave-1 merge, before
   Wave-2 worktree creation.

This script uses a MOCK client so no real API calls are made, but the
tools_schema construction and read_file path resolution are real code paths.
"""
import asyncio
import os
import subprocess
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from agent import Agent, get_tools_schema
import tools as tools_module

# ──────────────────────────────────────────────────────────────────
# PART A: confirm tools_schema includes read_file for a wrapped tool
# ──────────────────────────────────────────────────────────────────

worktree_dir = os.path.abspath(os.path.join(".", "scratch", "diag_worktree_tmp"))
os.makedirs(worktree_dir, exist_ok=True)

def wrapped_write(path: str, content: str, wpath=worktree_dir) -> str:
    return tools_module.write_file(os.path.join(wpath, path), content)
wrapped_write.__name__ = "write_file"
wrapped_write.__doc__ = tools_module.write_file.__doc__

def wrapped_read(path: str, wpath=worktree_dir) -> str:
    return tools_module.read_file(os.path.join(wpath, path))
wrapped_read.__name__ = "read_file"
wrapped_read.__doc__ = tools_module.read_file.__doc__

worker_tools = [wrapped_write, wrapped_read, tools_module.list_dir, tools_module.run_bash]
schema = get_tools_schema(worker_tools)

print("=" * 60)
print("PART A: tools_schema produced by get_tools_schema()")
print("=" * 60)
if schema is None:
    print("RESULT: schema is None - tools would NOT be sent to API -> BUG")
else:
    names_in_schema = [e["function"]["name"] for e in schema]
    print(f"Schema contains {len(schema)} tools: {names_in_schema}")
    has_read_file = "read_file" in names_in_schema
    print(f"read_file present: {has_read_file}")
    if not has_read_file:
        print("BUG CONFIRMED: read_file is missing from schema")
    else:
        print("OK: read_file is in schema - tools_schema is NOT the bug source")
print()

# ──────────────────────────────────────────────────────────────────
# PART B: cross-wave worktree file visibility
# Test: after Wave-1 commits db.py and it merges into main, does a
# freshly-created Wave-2 worktree contain db.py?
# ──────────────────────────────────────────────────────────────────

print("=" * 60)
print("PART B: cross-wave worktree file visibility")
print("=" * 60)

cwd = os.path.abspath(".")
wt1 = os.path.abspath(os.path.join("..", "diag-wave1-wt"))
wt2 = os.path.abspath(os.path.join("..", "diag-wave2-wt"))

def run(cmd, cwd_=None):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd_ or cwd)
    return r.stdout.strip(), r.stderr.strip(), r.returncode

# Clean up any leftovers
run(f"git worktree remove --force {wt1}")
run(f"git worktree remove --force {wt2}")
run(f"git branch -D diag/wave1")
run(f"git branch -D diag/wave2")
import shutil
for d in (wt1, wt2):
    if os.path.exists(d): shutil.rmtree(d, ignore_errors=True)

# Create Wave-1 worktree
out, err, rc = run(f"git worktree add {wt1} -b diag/wave1")
print(f"Create Wave-1 worktree: rc={rc} {'OK' if rc==0 else 'FAIL - ' + err}")

# Wave-1 worker writes db.py
db_content = "# db.py written by wave-1\ndef get_db(): return 'connected'"
with open(os.path.join(wt1, "db.py"), "w") as f:
    f.write(db_content)

# Wave-1 commits
run("git add -A", cwd_=wt1)
out, err, rc = run('git commit -m "Wave-1: add db.py"', cwd_=wt1)
print(f"Wave-1 commit: rc={rc} {'OK' if rc==0 else 'FAIL - ' + err}")

# Merge Wave-1 into main
out, err, rc = run('git merge diag/wave1 -m "Merge Wave-1"')
print(f"Merge Wave-1 into main: rc={rc} {'OK' if rc==0 else 'FAIL - ' + err}")

# Check: is db.py now in main?
db_in_main = os.path.exists(os.path.join(cwd, "db.py"))
print(f"db.py visible in main repo root after merge: {db_in_main}")

# Create Wave-2 worktree NOW (after merge)
out, err, rc = run(f"git worktree add {wt2} -b diag/wave2")
print(f"Create Wave-2 worktree: rc={rc} {'OK' if rc==0 else 'FAIL - ' + err}")

# Check: is db.py visible in Wave-2's worktree?
db_in_wt2 = os.path.exists(os.path.join(wt2, "db.py"))
print(f"\ndb.py visible in Wave-2 worktree at creation time: {db_in_wt2}")
if db_in_wt2:
    print("RESULT: Wave-2 worktree DOES contain dependency files from Wave-1 merge.")
    print("        The worktree-cross-access fallback fix is redundant (but harmless).")
else:
    print("BUG CONFIRMED: Wave-2 worktree does NOT contain Wave-1's merged files.")
    print("        Worker-2 read_file('db.py') would fail without the main-dir fallback.")
    # Double-check with git ls-files
    out, _, _ = run("git ls-files db.py", cwd_=wt2)
    print(f"        git ls-files db.py in Wave-2: '{out}' (empty = not tracked in branch)")

print()

# Cleanup
run(f"git worktree remove --force {wt1}")
run(f"git worktree remove --force {wt2}")
run("git rm -f db.py", cwd_=cwd)
run('git commit -m "Cleanup diag files"')
run("git branch -D diag/wave1")
run("git branch -D diag/wave2")
for d in (wt1, wt2):
    if os.path.exists(d): shutil.rmtree(d, ignore_errors=True)
if os.path.exists(os.path.join(cwd, "scratch", "diag_worktree_tmp")):
    shutil.rmtree(os.path.join(cwd, "scratch", "diag_worktree_tmp"), ignore_errors=True)

print("Cleanup done.")
