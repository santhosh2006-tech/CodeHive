from typing import Dict

registries: Dict[str, str] = {}

def register_service(service_name: str, service_url: str):
    registries[service_name] = service_url

def get_service_url(service_name: str) -> str:
    return registries.get(service_name)
