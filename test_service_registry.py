import unittest
from service_registry import ServiceRegistry

class TestServiceRegistry(unittest.TestCase):
    def test_service_registry(self):
        service_registry = ServiceRegistry()
        self.assertIsNotNone(service_registry)

groups = unittest.TestLoader().loadTestsFromTestCase(TestServiceRegistry)
test_runner = unittest.TextTestRunner(verbosity=2)
test_runner.run(groups)