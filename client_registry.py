from service_registry import ServiceRegistry

class ClientRegistry:
    def __init__(self, service_registry):
        self.service_registry = service_registry
        self.clients = {}

    def register_client(self, client_id, client_url):
        self.clients[client_id] = client_url

    def get_client_url(self, client_id):
        return self.clients.get(client_id)

    def unregister_client(self, client_id):
        if client_id in self.clients:
            del self.clients[client_id]
