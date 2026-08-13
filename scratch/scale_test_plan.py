import os
import sys
from dotenv import load_dotenv
load_dotenv()

import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from providers import get_providers
from orchestrator import Orchestrator

def main():
    providers = get_providers()
    if not providers:
        print("Error: No providers configured.")
        return
        
    orchestrator = Orchestrator(providers=providers, tools=[])
    
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

    print("Planning Scale Task...")
    subtasks = orchestrator.plan(scale_prompt)
    
    print("\n=== GENERATED PLAN BREAKDOWN ===")
    for st in subtasks:
        print(f"Subtask {st['id']}: {st['title']}")
        print(f"  Depends On: {st.get('depends_on', [])}")
        print(f"  Instructions: {st['instructions']}\n")
    print("================================")

if __name__ == "__main__":
    main()
