import os

class ServiceRegistry:
    def __init__(self):
        self.services = {}

    def register(self, name, url):
        self.services[name] = url

    def unregister(self, name):
        if name in self.services:
            del self.services[name]

    def get_service(self, name):
        return self.services.get(name)
