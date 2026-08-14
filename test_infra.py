import unittest
from infra import Infra

class TestInfra(unittest.TestCase):
    def test_create_infra(self):
        infra = Infra()
        infra_id = infra.create_infra('test_infra')
        self.assertIsNotNone(infra_id)

    def test_get_infra(self):
        infra = Infra()
        infra_id = infra.create_infra('test_infra')
        infra_obj = infra.get_infra(infra_id)
        self.assertEqual(infra_obj['name'], 'test_infra')

if __name__ == '__main__':
    unittest.main()