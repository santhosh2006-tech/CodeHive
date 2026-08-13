import os
import sys
from dotenv import load_dotenv
load_dotenv()

# Ensure parent directory is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from providers import get_providers
from orchestrator import Orchestrator

def main():
    """Live verification test for Git merge conflict reconciliation using real LLM API."""
    providers = get_providers()
    if not providers:
        print("Error: No providers configured. Make sure GROQ_API_KEY is set in .env.")
        return
        
    orchestrator = Orchestrator(providers=providers, tools=[])
    
    # Actual conflict content from test_22 (Worker A and Worker B print statements)
    conf_content = """<<<<<<< HEAD
print('hello from worker A')
=======
print('hello from worker B')
>>>>>>> task/2"""

    print("Sending conflict markers to real Orchestrator._reconcile_conflict...")
    print("--- INPUT ---")
    print(conf_content)
    print("-------------\n")
    
    # Invoke the real _reconcile_conflict method
    resolved = orchestrator._reconcile_conflict("temp_conflict.py", conf_content)
    
    print("--- LIVE LLM RESOLVED OUTPUT ---")
    print(resolved)
    print("--------------------------------")

if __name__ == "__main__":
    main()
