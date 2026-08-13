import unittest
from infra import Infra

class TestInfra(unittest.TestCase):
    def test_create_infra(self):
        infra = Infra()
        infra_id = infra.create_infra('example_infra')
        self assertNotEqual(infra_id, None)

    def test_get_infra(self):
        infra = Infra()
        infra_id = infra.create_infra('example_infra')
        infra_resource = infra.get_infra(infra_id)
        self.assertEqual(infra_resource['name'], 'example_infra')

if __name__ == '__main__':
    unittest.main()