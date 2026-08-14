import sqlite3

class UserDB:
    def __init__(self, db_name):
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self.create_table()

    def create_table(self):
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS users
            (id INTEGER PRIMARY KEY, username TEXT, email TEXT)
        """)
        self.conn.commit()

    def insert_user(self, username, email):
        self.cursor.execute("INSERT INTO users (username, email) VALUES (?, ?)", (username, email))
        self.conn.commit()

    def get_user(self, id):
        self.cursor.execute("SELECT * FROM users WHERE id=?", (id,))
        return self.cursor.fetchone()

    def close(self):
        self.conn.close()
