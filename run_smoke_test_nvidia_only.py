import asyncio
import os
from providers import get_providers
from main import process_task

async def main():
    # Set the real NVIDIA key
    os.environ["NVIDIA_API_KEY"] = "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"
    
    # Force it to use NVIDIA-only to verify the NVIDIA NIM integration works end-to-end
    providers = get_providers()
    nvidia_provider = [p for p in providers if p["name"] == "nvidia"]
    
    if not nvidia_provider:
        print("Error: NVIDIA provider is not configured.")
        return
        
    print("Running live NVIDIA-only smoke test...")
    target_file = "math_helpers.py"
    if os.path.exists(target_file):
        os.remove(target_file)
        
    prompt = "Create a simple math module math_helpers.py with add, subtract, multiply, and divide functions."
    
    try:
        await process_task(nvidia_provider, prompt)
        
        if os.path.exists(target_file):
            print("\nNVIDIA SMOKE TEST SUCCESS!")
            print("Created file contents:")
            with open(target_file, "r") as f:
                print(f.read())
        else:
            print("\nNVIDIA SMOKE TEST FAILURE: Target file was not created.")
            
    except Exception as e:
        print(f"\nNVIDIA SMOKE TEST FAILURE: Exception occurred: {e}")
        
    finally:
        if os.path.exists(target_file):
            os.remove(target_file)

if __name__ == "__main__":
    asyncio.run(main())
