import unittest
from service_registry import ServiceRegistry

class TestServiceRegistry(unittest.TestCase):
    def test_register_service(self):
        service_registry = ServiceRegistry()
        service_registry.register_service("test_service", "test_url")
        self.assertIn("test_service", service_registry.get_services())

    def test_get_services(self):
        service_registry = ServiceRegistry()
        service_registry.register_service("test_service", "test_url")
        self.assertIn("test_service", service_registry.get_services())

if __name__ == '__main__':
    unittest.main()