import unittest
from api_gateway import ApiGateway

class TestApiGateway(unittest.TestCase):
    def test_route_request(self):
        api_gateway = ApiGateway()
        response = api_gateway.route_request('GET', '/test_service', {'header1': 'value1'})
        self.assertEqual(response.status_code, 200)

if __name__ == '__main__':
    unittest.main()