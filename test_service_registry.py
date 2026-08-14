import unittest
from service_registry import ServiceRegistry

class TestServiceRegistry(unittest.TestCase):
    def test_register_service(self):
        service_registry = ServiceRegistry()
        service_id = service_registry.register_service('test_service', 'http://localhost:9204')
        self.assertIsNotNone(service_id)

    def test_get_service(self):
        service_registry = ServiceRegistry()
        service_id = service_registry.register_service('test_service', 'http://localhost:9204')
        service = service_registry.get_service(service_id)
        self.assertEqual(service['name'], 'test_service')

if __name__ == '__main__':
    unittest.main()