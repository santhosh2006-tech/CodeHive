from user_db import UserDB

class ClientUser:
    def __init__(self):
        self.user_db = UserDB()

    def add_user(self, name, email):
        self.user_db.insert_user(name, email)

    def get_users(self):
        return self.user_db.get_users()

    def close(self):
        self.user_db.close()
