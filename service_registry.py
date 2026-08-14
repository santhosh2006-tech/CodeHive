# Service Registry

class ServiceRegistry:
    def __init__(self):
        self.services = {}

    def register(self, service_name, service_instance):
        self.services[service_name] = service_instance

    def get_service(self, service_name):
        return self.services.get(service_name)
