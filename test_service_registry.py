import unittest
from service_registry import ServiceRegistry

class TestServiceRegistry(unittest.TestCase):
    def test_register_service(self):
        service_registry = ServiceRegistry()
        service_registry.register_service('test_service', 'http://localhost:9204/test_service')
        self.assertIn('test_service', service_registry.get_registered_services())

if __name__ == '__main__':
    unittest.main()