class ClientRegistry:
    def __init__(self):
        self.clients = {}

    def register(self, client_id, client):
        self.clients[client_id] = client

    def unregister(self, client_id):
        if client_id in self.clients:
            del self.clients[client_id]

    def get_client(self, client_id):
        return self.clients.get(client_id)
