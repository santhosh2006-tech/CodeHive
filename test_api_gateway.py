import unittest
from api_gateway import ApiGateway

class TestApiGateway(unittest.TestCase):
    def test_create_api(self):
        api_gateway = ApiGateway()
        api_id = api_gateway.create_api('example_api', '/example')
        self assertNotEqual(api_id, None)

    def test_get_api(self):
        api_gateway = ApiGateway()
        api_id = api_gateway.create_api('example_api', '/example')
        api = api_gateway.get_api(api_id)
        self.assertEqual(api['name'], 'example_api')
        self.assertEqual(api['path'], '/example')

if __name__ == '__main__':
    unittest.main()