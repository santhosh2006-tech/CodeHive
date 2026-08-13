from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from logger import logger

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String)
    password = Column(String)

    def __repr__(self):
        return f'User(id={self.id}, username={self.username}, password={self.password})'

def create_db():
    engine = create_engine('sqlite:///user.db')
    Base.metadata.create_all(engine)
    return engine