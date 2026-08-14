import unittest
from infra import Infra

class TestInfra(unittest.TestCase):
    def test_infra_setup(self):
        infra = Infra()
        self assertEqual(infra.setup(), True)

def main():
    unittest.main()
if __name__ == '__main__':
    main()