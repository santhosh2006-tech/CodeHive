import logging
from logger import Logger

logger = Logger().get_logger()

class ServiceRegistry:
    def __init__(self):
        self.services = {}

    def register(self, service_name, service_url):
        self.services[service_name] = service_url
        logger.info(f'Registered service {service_name} with URL {service_url}')

    def unregister(self, service_name):
        if service_name in self.services:
            del self.services[service_name]
            logger.info(f'Unregistered service {service_name}')
        else:
            logger.warning(f'Service {service_name} is not registered')

    def get_service_url(self, service_name):
        return self.services.get(service_name)
