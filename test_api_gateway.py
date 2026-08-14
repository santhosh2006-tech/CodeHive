import unittest
from api_gateway import ApiGateway

class TestApiGateway(unittest.TestCase):
    def test_api_request(self):
        api_gateway = ApiGateway()
        response = api_gateway.handle_request("test_request")
        self assertNotEqual(response, None)

def main():
    unittest.main()
if __name__ == '__main__':
    main()