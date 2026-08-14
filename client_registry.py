import os

class ClientRegistry:
    def __init__(self):
        self.clients = {}

    def register(self, name, url):
        self.clients[name] = url

    def unregister(self, name):
        if name in self.clients:
            del self.clients[name]

    def get_client(self, name):
        return self.clients.get(name)
