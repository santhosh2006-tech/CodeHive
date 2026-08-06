import os
from openai import OpenAI

os.environ["NVIDIA_API_KEY"] = "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"
client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=os.environ["NVIDIA_API_KEY"],
    timeout=30.0
)

try:
    models = client.models.list()
    model_ids = sorted([m.id for m in models.data])
    print(f"Total models available: {len(model_ids)}")
    print("\n--- MODEL IDs ---")
    for mid in model_ids:
        print(mid)
    print("-----------------")
except Exception as e:
    print("Error:", e)
