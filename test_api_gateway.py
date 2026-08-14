import unittest
from api_gateway import ApiGateway

class TestApiGateway(unittest.TestCase):
    def test_handle_request(self):
        api_gateway = ApiGateway()
        response = api_gateway.handle_request("test_request")
        self.assertEqual(response.status_code, 200)

if __name__ == '__main__':
    unittest.main()