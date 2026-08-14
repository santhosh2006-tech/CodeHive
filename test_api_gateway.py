import unittest
from api_gateway import ApiGateway

class TestApiGateway(unittest.TestCase):
    def test_create_api(self):
        api_gateway = ApiGateway()
        api_id = api_gateway.create_api('test_api', 'http://localhost:9204')
        self.assertIsNotNone(api_id)

    def test_get_api(self):
        api_gateway = ApiGateway()
        api_id = api_gateway.create_api('test_api', 'http://localhost:9204')
        api = api_gateway.get_api(api_id)
        self.assertEqual(api['name'], 'test_api')

if __name__ == '__main__':
    unittest.main()