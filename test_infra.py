import unittest
from infra import Infra

class TestInfra(unittest.TestCase):
    def test_create_resources(self):
        infra = Infra()
        infra.create_resources()
        self.assertTrue(infra.resources_created)

if __name__ == '__main__':
    unittest.main()