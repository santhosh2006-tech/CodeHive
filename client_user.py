from user_db import UserDB

class ClientUser:
    def __init__(self, user_db: UserDB):
        self.user_db = user_db

    def register(self, username: str, password: str):
        self.user_db.add_user(username, password)

    def login(self, username: str, password: str):
        return self.user_db.get_user(username) == password

    def update_password(self, username: str, new_password: str):
        self.user_db.update_user(username, new_password)

    def delete_account(self, username: str):
        self.user_db.delete_user(username)