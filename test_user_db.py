import unittest
from user_db import UserDB

class TestUserDB(unittest.TestCase):
    def test_user_db(self):
        user_db = UserDB()
        self.assertIsNotNone(user_db)

groups = unittest.TestLoader().loadTestsFromTestCase(TestUserDB)
test_runner = unittest.TextTestRunner(verbosity=2)
test_runner.run(groups)