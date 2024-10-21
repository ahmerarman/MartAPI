from fastapi.testclient import TestClient
import pytest
from sqlmodel import Field, Session, SQLModel, create_engine

# https://sqlmodel.tiangolo.com/tutorial/fastapi/tests/#override-a-dependency
from app.db import get_session
from app.main import app

from app import settings

# https://fastapi.tiangolo.com/tutorial/testing/
# https://realpython.com/python-assert-statement/
# https://understandingdata.com/posts/list-of-python-assert-statements-for-unit-tests/

# postgresql://ziaukhan:oSUqbdELz91i@ep-polished-waterfall-a50jz332.us-east-2.aws.neon.tech/neondb?sslmode=require

connection_string = str(settings.TEST_DATABASE_URL).replace(
    "postgresql", "postgresql+psycopg")

if connection_string is None:
    raise EnvironmentError("TEST_DATABASE_URL not found in .env file.")

@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine(connection_string, connect_args={"sslmode": "require"}, pool_recycle=300, echo=True)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session

@pytest.fixture(name="client")
def client_fixture(session: Session):
    def get_session_override():
        return session
    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()

def test_root_path()->None:
    client = TestClient(app=app)
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"Hello": "Ahmer Arman"}
