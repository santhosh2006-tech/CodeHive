import unittest
from user_db import UserDB

class TestUserDB(unittest.TestCase):
    def test_get_user(self):
        user_db = UserDB()
        user = user_db.get_user('test_user')
        self.assertEqual(user.username, 'test_user')

if __name__ == '__main__':
    unittest.main()