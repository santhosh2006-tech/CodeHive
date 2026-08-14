from user_db import UserDB

class ClientUser:
    def __init__(self, db_name):
        self.user_db = UserDB(db_name)

    def insert_user(self, username, email):
        self.user_db.insert_user(username, email)

    def get_user(self, id):
        return self.user_db.get_user(id)
