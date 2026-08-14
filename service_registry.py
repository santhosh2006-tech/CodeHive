class ServiceRegistry:
    def __init__(self):
        self.services = {}

    def register(self, service_name, service):
        self.services[service_name] = service

    def unregister(self, service_name):
        if service_name in self.services:
            del self.services[service_name]

    def get_service(self, service_name):
        return self.services.get(service_name)
