DB_HOST = 'localhost'
DB_PORT = 5432
DB_USERNAME = 'username'
DB_PASSWORD = 'password'
DB_NAME = 'user_db'

SQLALCHEMY_DATABASE_URI = f'postgresql://{DB_USERNAME}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'