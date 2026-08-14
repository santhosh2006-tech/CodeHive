# client_registry.py
import requests
from config import REGISTRY_SERVICE_HOST, REGISTRY_SERVICE_PORT

class ClientRegistry:
    def __init__(self, service_name, host, port):
        self.service_name = service_name
        self.host = host
        self.port = port
        self.registry_url = f'http://{REGISTRY_SERVICE_HOST}:{REGISTRY_SERVICE_PORT}'

    def register(self):
        data = {'name': self.service_name, 'host': self.host, 'port': self.port}
        response = requests.post(f'{self.registry_url}/register', json=data)
        return response.json(), response.status_code

    def deregister(self):
        data = {'name': self.service_name}
        response = requests.post(f'{self.registry_url}/deregister', json=data)
        return response.json(), response.status_code

    def get_services(self):
        response = requests.get(f'{self.registry_url}/services')
        return response.json(), response.status_code