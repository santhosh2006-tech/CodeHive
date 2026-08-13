import sqlite3
from config import DB_NAME

class UserDB:
    def __init__(self):
        self.conn = sqlite3.connect(DB_NAME)
        self.cursor = self.conn.cursor()
        self.create_table()

    def create_table(self):
        self.cursor.execute ''''''
        CREATE TABLE IF NOT EXISTS users
        (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, email TEXT)
        ''''''
        self.conn.commit()

    def insert_user(self, name, email):
        self.cursor.execute ''''''
        INSERT INTO users (name, email) VALUES (?, ?)
        '''''', (name, email)
        self.conn.commit()

    def get_users(self):
        self.cursor.execute ''''''
        SELECT * FROM users
        ''''''
        return self.cursor.fetchall()

    def close(self):
        self.conn.close()
