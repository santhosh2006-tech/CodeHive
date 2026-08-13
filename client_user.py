from user_db import User, create_db
from sqlalchemy.orm import sessionmaker
from logger import logger

def get_user(username):
    engine = create_db()
    Session = sessionmaker(bind=engine)
    session = Session()
    user = session.query(User).filter_by(username=username).first()
    session.close()
    return user