# Client Registry

class ClientRegistry:
    def __init__(self):
        self.clients = {}

    def register_client(self, client_id, client_url):
        self.clients[client_id] = client_url

    def get_client_url(self, client_id):
        return self.clients.get(client_id)
