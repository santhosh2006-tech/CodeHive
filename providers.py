import os
from groq import Groq
from openai import OpenAI

def get_providers():
    """Initializes and returns the list of available providers based on configured environment keys."""
    providers = []
    
    # Groq API configuration
    if os.environ.get("GROQ_API_KEY"):
        providers.append({
            "name": "groq",
            "client": Groq(api_key=os.environ["GROQ_API_KEY"], timeout=30.0),
            "model": "llama-3.3-70b-versatile"
        })
        
    # NVIDIA NIM API configuration
    if os.environ.get("NVIDIA_API_KEY"):
        providers.append({
            "name": "nvidia",
            "client": OpenAI(
                base_url="https://integrate.api.nvidia.com/v1",
                api_key=os.environ["NVIDIA_API_KEY"],
                timeout=30.0
            ),
            "model": "meta/llama-3.1-8b-instruct"
        })
        
    return providers
