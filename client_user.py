from user_db import UserDB

class ClientUser:
    def __init__(self, db_name):
        self.user_db = UserDB(db_name)

    def add_user(self, username, password):
        self.user_db.add_user(username, password)

    def get_user(self, username):
        return self.user_db.get_user(username)
