from user_db import UserDB

class ClientUser:
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.user_db = UserDB('users.db')

    def register(self):
        if self.user_db.get_user(self.username):
            return False
        self.user_db.insert_user(self.username, self.password)
        return True

    def login(self):
        user = self.user_db.get_user(self.username)
        if user and user[2] == self.password:
            return True
        return False
