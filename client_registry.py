from typing import Dict

registries: Dict[str, str] = {}

def register_client(client_name: str, client_url: str):
    registries[client_name] = client_url

def get_client_url(client_name: str) -> str:
    return registries.get(client_name)
