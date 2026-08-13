import unittest
from service_registry import ServiceRegistry

class TestServiceRegistry(unittest.TestCase):
    def test_register_service(self):
        service_registry = ServiceRegistry()
        service_id = service_registry.register_service('example_service', 'http://example.com')
        self assertNotEqual(service_id, None)

    def test_get_service(self):
        service_registry = ServiceRegistry()
        service_id = service_registry.register_service('example_service', 'http://example.com')
        service = service_registry.get_service(service_id)
        self.assertEqual(service['name'], 'example_service')
        self.assertEqual(service['url'], 'http://example.com')

if __name__ == '__main__':
    unittest.main()