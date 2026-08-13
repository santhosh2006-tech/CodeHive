import unittest
from user_db import UserDB

class TestUserDB(unittest.TestCase):
    def test_create_user(self):
        user_db = UserDB()
        user_id = user_db.create_user('John Doe', 'johndoe@example.com')
        self assertNotEqual(user_id, None)

    def test_get_user(self):
        user_db = UserDB()
        user_id = user_db.create_user('John Doe', 'johndoe@example.com')
        user = user_db.get_user(user_id)
        self.assertEqual(user['name'], 'John Doe')
        self.assertEqual(user['email'], 'johndoe@example.com')

if __name__ == '__main__':
    unittest.main()