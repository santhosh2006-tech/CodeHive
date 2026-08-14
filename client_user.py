from user_db import UserDB

class ClientUser:
    def __init__(self, db_name):
        self.user_db = UserDB(db_name)

    def add_user(self, name, email):
        self.user_db.insert_user(name, email)

    def get_users(self):
        return self.user_db.get_users()

    def close_connection(self):
        self.user_db.close_connection()
