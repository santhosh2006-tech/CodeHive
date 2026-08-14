import unittest
from infra import Infra

class TestInfra(unittest.TestCase):
    def test_infra(self):
        infra = Infra()
        self.assertIsNotNone(infra)

groups = unittest.TestLoader().loadTestsFromTestCase(TestInfra)
test_runner = unittest.TextTestRunner(verbosity=2)
test_runner.run(groups)