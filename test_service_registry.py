import unittest
from service_registry import ServiceRegistry

class TestServiceRegistry(unittest.TestCase):
    def test_service_registration(self):
        service_registry = ServiceRegistry()
        service_id = service_registry.register_service("test_service")
        self assertNotEqual(service_id, None)

def main():
    unittest.main()
if __name__ == '__main__':
    main()