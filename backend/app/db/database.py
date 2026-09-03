import os
from sqlmodel import SQLModel, create_engine, Session

DB_PATH = os.getenv("DATABASE_URL", "sqlite:///./asc_database.db")
connect_args = {"check_same_thread": False} if DB_PATH.startswith("sqlite") else {}

engine = create_engine(DB_PATH, echo=False, connect_args=connect_args)

def init_db():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session
