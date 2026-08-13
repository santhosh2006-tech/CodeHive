import asyncio
import os
from providers import get_providers
from main import process_task

async def main():
    # Set invalid primary key to trigger fallback
    os.environ["GROQ_API_KEY"] = "gsk_invalidkey123"
    # Set valid secondary key
    if not os.environ.get("GROQ_API_KEY_2"): print("Set GROQ_API_KEY_2"); return
    
    # Reload providers
    providers = get_providers()
    print("Available Providers:", [p["name"] for p in providers])
    
    target_file = "math_helpers.py"
    if os.path.exists(target_file):
        os.remove(target_file)
        
    print("\nRunning live fallback verification test (Primary is invalid)...")
    prompt = "Create a simple math module math_helpers.py with add, subtract, multiply, and divide functions."
    
    try:
        await process_task(providers, prompt)
        
        if os.path.exists(target_file):
            print("\nLIVE DUAL-GROQ FALLBACK SUCCESS!")
            print("Created file contents:")
            with open(target_file, "r") as f:
                print(f.read())
        else:
            print("\nLIVE DUAL-GROQ FALLBACK FAILURE: Target file was not created.")
            
    except Exception as e:
        print(f"\nLIVE DUAL-GROQ FALLBACK FAILURE: Exception occurred: {e}")
        
    finally:
        if os.path.exists(target_file):
            os.remove(target_file)

if __name__ == "__main__":
    asyncio.run(main())
