import unittest
from api_gateway import ApiGateway

class TestApiGateway(unittest.TestCase):
    def test_api_gateway(self):
        api_gateway = ApiGateway()
        self.assertIsNotNone(api_gateway)

groups = unittest.TestLoader().loadTestsFromTestCase(TestApiGateway)
test_runner = unittest.TextTestRunner(verbosity=2)
test_runner.run(groups)