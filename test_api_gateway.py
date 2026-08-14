import unittest
from api_gateway import ApiGateway

class TestApiGateway(unittest.TestCase):
    def test_handle_request(self):
        api_gateway = ApiGateway()
        request = {'method': 'GET', 'path': '/test'}
        response = api_gateway.handle_request(request)
        self.assertEqual(response['status'], 200)

if __name__ == '__main__':
    unittest.main()