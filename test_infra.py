import unittest
from infra import Infra

class TestInfra(unittest.TestCase):
    def test_create_infra(self):
        infra = Infra()
        infra.create_infra()
        self.assertTrue(infra.is_infra_created())

if __name__ == '__main__':
    unittest.main()