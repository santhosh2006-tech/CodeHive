import unittest
from infra import Infra

class TestInfra(unittest.TestCase):
    def test_create_infra(self):
        infra = Infra()
        infra.create_infra("test_infra")
        self.assertTrue(infra.check_infra("test_infra"))

if __name__ == '__main__':
    unittest.main()