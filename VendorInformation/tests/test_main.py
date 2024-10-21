from fastapi.testclient import TestClient
import pytest
from sqlmodel import Field, Session, SQLModel, create_engine

# https://sqlmodel.tiangolo.com/tutorial/fastapi/tests/#override-a-dependency
from app.main import app, get_session, VendorInformation

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
    engine = create_engine(connection_string, connect_args={}, pool_recycle=300, echo=True)
    #SQLModel.metadata.create_all(engine)
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

def test_root_path(client: TestClient)->None:
#    client = TestClient(app=app)
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"Hello": "Ahmer Arman"}


def test_create_vendor(client: TestClient):
#    connection_string = str(settings.TEST_DATABASE_URL).replace(
#        "postgresql", "postgresql+psycopg")
#    if connection_string is None:
#        raise EnvironmentError("TEST_DATABASE_URL not found in .env file.")

#    engine = create_engine(
#        connection_string, connect_args={"sslmode": "require"}, pool_recycle=300)

#    SQLModel.metadata.create_all(engine)  

#    with Session(engine) as session:  

#        def get_session_override():  
#                return session  

#        app.dependency_overrides[get_session] = get_session_override 

#        client = TestClient(app=app)

        # vendor_content = "buy bread"

        response = client.post("/VendorInformation/",
            json={
                "VendorName": "ABC Company",
                "VendorAddress": "25th street",
                "NTN_No": "123456",
                "STN_No": "123456",
                "ContactPerson": "Mr. A",
                "Contact_No": "123456",
                "Email": "abc@abc.com",
                "Enabled": True,
                "BankAC_No": "123456",
                "VendorCode": 1
                }
        )

        data = response.json()

        assert response.status_code == 200
        assert data["VendorName"] == "ABC Company"
        assert data["VendorAddress"] == "25th street"
        assert data["NTN_No"] == "123456"
        assert data["STN_No"] == "123456"
        assert data["ContactPerson"] == "Mr. A"
        assert data["Contact_No"] == "123456"
        assert data["Email"] == "abc@abc.com"
        assert data["Enabled"] == True
        assert data["BankAC_No"] == "123456"
        assert data["VendorCode"] is not None

