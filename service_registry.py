# Service Registry

class ServiceRegistry:
    def __init__(self):
        self.services = {}

    def register_service(self, service_name, service_url):
        self.services[service_name] = service_url

    def get_service_url(self, service_name):
        return self.services.get(service_name)
