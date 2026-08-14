# Client Registry

class ClientRegistry:
    def __init__(self):
        self.clients = {}

    def register(self, client_id, client_instance):
        self.clients[client_id] = client_instance

    def get_client(self, client_id):
        return self.clients.get(client_id)
