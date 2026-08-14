import unittest
from user_db import UserDB

class TestUserDB(unittest.TestCase):
    def test_add_user(self):
        user_db = UserDB()
        user_db.add_user('test_user', 'test_password')
        self.assertIn('test_user', user_db.get_users())

    def test_get_users(self):
        user_db = UserDB()
        user_db.add_user('test_user', 'test_password')
        self.assertEqual(user_db.get_users(), ['test_user'])

if __name__ == '__main__':
    unittest.main()