import unittest
from user_db import UserDB

class TestUserDB(unittest.TestCase):
    def test_create_user(self):
        user_db = UserDB()
        user_db.create_user("test_user", "test_password")
        self.assertTrue(user_db.check_user("test_user", "test_password"))

    def test_check_user(self):
        user_db = UserDB()
        user_db.create_user("test_user", "test_password")
        self.assertTrue(user_db.check_user("test_user", "test_password"))
        self.assertFalse(user_db.check_user("test_user", "wrong_password"))

if __name__ == '__main__':
    unittest.main()