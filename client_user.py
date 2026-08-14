from user_db import UserDB

class ClientUser:
    def __init__(self, db_name):
        self.user_db = UserDB(db_name)

    def register(self, username, password):
        if self.user_db.get_user(username):
            return False
        self.user_db.insert_user(username, password)
        return True

    def login(self, username, password):
        user = self.user_db.get_user(username)
        if user and user[2] == password:
            return True
        return False
