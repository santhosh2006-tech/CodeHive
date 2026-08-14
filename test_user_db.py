import unittest
from user_db import UserDB

class TestUserDB(unittest.TestCase):
    def test_create_user(self):
        user_db = UserDB()
        user_id = user_db.create_user('test_user', 'test_password')
        self.assertIsNotNone(user_id)

    def test_get_user(self):
        user_db = UserDB()
        user_id = user_db.create_user('test_user', 'test_password')
        user = user_db.get_user(user_id)
        self.assertEqual(user['username'], 'test_user')

if __name__ == '__main__':
    unittest.main()