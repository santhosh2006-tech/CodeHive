import os
import sys
import asyncio
from dotenv import load_dotenv
load_dotenv()

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from providers import get_providers
from orchestrator import Orchestrator
import tools

async def main():
    providers = get_providers()
    if not providers:
        print("Error: No providers configured.")
        return
        
    orchestrator = Orchestrator(providers=providers, tools=[tools.write_file, tools.read_file, tools.run_bash])
    
    scale_prompt = """Build a modular Python-based microservices catalog with 10+ files:
1. config.py: Holds global configuration parameters.
2. logger.py: Implements log formatting.
3. user_db.py: Database storage model for users.
4. service_registry.py: Storage model for service registrations.
5. client_user.py: Client library for interacting with user db.
6. client_registry.py: Client library for service registry.
7. api_gateway.py: Flask API routing gateway.
8. test_user_db.py: Unit tests for user db.
9. test_service_registry.py: Unit tests for service registry.
10. test_api_gateway.py: Gateway tests.
11. test_infra.py: Infrastructure configuration tests.
12. README.md: Service catalog documentation.

Subtasks must be created for parallel workers:
- Worker 1 implements user_db.py, client_user.py, and writes database configurations to config.py.
- Worker 2 implements service_registry.py, client_registry.py, and writes registry configurations to config.py (concurrently overlapping and conflicting with Worker 1 on config.py).
- Worker 3 implements the API gateway api_gateway.py (which imports client libraries and maps endpoints) and updates config.py with gateway route properties (runs in Wave 2 on top of Wave 1's merged output).
- Worker 4 writes test_user_db.py, test_service_registry.py, test_api_gateway.py, test_infra.py, and README.md.

Configure appropriate depends_on fields to ensure correct wave execution ordering.
Ensure that Subtask 3 depends on Subtask 1 and Subtask 2, and Subtask 4 depends on Subtask 3."""

    print("[Scale Test] Planning microservices catalog...")
    subtasks = orchestrator.plan(scale_prompt)
    
    print("\n=== PLAN BREAKDOWN ===")
    for st in subtasks:
        print(f"Subtask {st['id']}: {st['title']}")
        print(f"  Depends On: {st.get('depends_on', [])}")
    print("======================\n")
    
    # Initialize base empty files and commit them to git so that worktrees merge cleanly
    # ONLY initialize files that don't already exist or contain only placeholders
    base_files = ["config.py", "logger.py", "user_db.py", "service_registry.py", 
                  "client_user.py", "client_registry.py", "api_gateway.py", 
                  "test_user_db.py", "test_service_registry.py", "test_api_gateway.py", 
                  "test_infra.py", "README.md"]
                  
    print("Initializing base files in Git (only if missing or placeholder)...")
    files_to_add = []
    for f in base_files:
        should_init = False
        if not os.path.exists(f):
            should_init = True
        else:
            # Check if file contains only placeholder content (< 50 bytes or starts with "# Base file")
            try:
                with open(f, "r", encoding="utf-8") as f_check:
                    content = f_check.read()
                    if len(content) < 50 or content.strip().startswith("# Base file"):
                        should_init = True
            except Exception:
                should_init = True
        
        if should_init:
            with open(f, "w", encoding="utf-8") as f_out:
                f_out.write("# Base file placeholder\n")
            files_to_add.append(f)
            print(f"  Initialized: {f}")
        else:
            print(f"  Skipped (has real content): {f}")
            
    import subprocess
    if files_to_add:
        subprocess.run("git add " + " ".join(files_to_add), shell=True, capture_output=True)
        subprocess.run('git commit -m "Initialize base files for scale test"', shell=True, capture_output=True)
        print(f"Committed {len(files_to_add)} new/placeholder files to main.")
    else:
        print("No files needed initialization - all have real content already.")
    
    print("Executing scale task waves...")
    try:
        results, conflicts, execution_warnings = await orchestrator.run_workers(subtasks)
        
        print("\n=== SCALE TEST RESULTS ===")
        print(f"Results Count: {len(results)}")
        print(f"Conflicts Count: {len(conflicts)}")
        print(f"Conflicts: {conflicts}")
        print(f"Execution Warnings: {execution_warnings}")
        print("==========================\n")
        
        # Verify file presence and contents
        print("=== VERIFYING PRODUCED FILES ===")
        for f in base_files:
            exists = os.path.exists(f)
            size = os.path.getsize(f) if exists else 0
            print(f"File: {f} | Exists: {exists} | Size: {size} bytes")
            if exists and f in ("config.py", "api_gateway.py"):
                with open(f, "r", encoding="utf-8") as file_read:
                    print(f"--- {f} Content ---")
                    print(file_read.read())
                    print("----------------------")
        print("================================")
        
    finally:
        print("Bypassing automatic cleanup to inspect generated files...")

if __name__ == "__main__":
    asyncio.run(main())
