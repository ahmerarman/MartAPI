from sqlmodel import create_engine, SQLModel, Session
from app import settings

connection_string = str(settings.DATABASE_URL).replace(
    "postgresql", "postgresql+psycopg"
)

if connection_string is None:
    raise EnvironmentError("DATABASE_URL not found in .env file.")

engine = create_engine(
    connection_string, connect_args={}, pool_recycle=300
)

def get_session():
    with Session(engine) as session:
        yield session

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
