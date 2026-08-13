import logging
from logger import Logger
from service_registry import ServiceRegistry

logger = Logger().get_logger()

class ClientRegistry:
    def __init__(self, registry):
        self.registry = registry

    def register(self, service_name, service_url):
        self.registry.register(service_name, service_url)

    def unregister(self, service_name):
        self.registry.unregister(service_name)

    def get_service_url(self, service_name):
        return self.registry.get_service_url(service_name)
