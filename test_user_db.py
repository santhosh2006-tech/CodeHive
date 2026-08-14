import unittest
from user_db import UserDB

class TestUserDB(unittest.TestCase):
    def test_user_creation(self):
        user_db = UserDB()
        user_id = user_db.create_user("test_user")
        self assertNotEqual(user_id, None)

def main():
    unittest.main()
if __name__ == '__main__':
    main()