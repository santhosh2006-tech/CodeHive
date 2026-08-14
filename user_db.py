from typing import Dict

class UserDB:
    def __init__(self):
        self.users: Dict[str, str] = {}

    def add_user(self, username: str, password: str):
        self.users[username] = password

    def get_user(self, username: str):
        return self.users.get(username)

    def update_user(self, username: str, password: str):
        if username in self.users:
            self.users[username] = password

    def delete_user(self, username: str):
        if username in self.users:
            del self.users[username]