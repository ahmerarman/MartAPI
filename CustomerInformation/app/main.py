# main.py
from contextlib import asynccontextmanager
from typing import Optional, Annotated

import requests # type: ignore

from app import settings
from sqlmodel import Field, Session, SQLModel, create_engine, select
from fastapi import FastAPI, Depends, HTTPException
from typing import AsyncGenerator
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer # type: ignore
import asyncio
import json


class CustomerInformation(SQLModel, table=True):
    CustomerID: Optional[int] = Field(default=None, primary_key=True)
    CustomerName: str = Field(default=None, index=True, max_length=50)
    CustomerAddress: str = Field(default=None, max_length=50)
    Contact_No: str = Field(default=None, max_length=20)
    Email: str = Field(default=None, max_length=20)
    Enabled: bool = Field(default=True)


class CustomerUpdate(SQLModel):
    CustomerName: str | None = None
    CustomerAddress: str | None = None
    Contact_No: str | None = None
    Email: str | None = None


async def patch_order_status(record_id: int):
#    api_url = f"http://api6:8000/OrderServices/{record_id}"
#    headers = {
#        "Content-Type": "application/json"
#    }
#    data = {
#        "Enabled": enabled
#    }
#    try:
#        response = requests.patch(api_url, headers=headers, json=data)
#        response.raise_for_status()
#    except requests.exceptions.RequestException as e:
#        raise HTTPException(status_code=response.status_code, detail=str(e))
    pass


async def fetch_customer_orders(customer: CustomerInformation):
#    api_url = f"http://api6:8000/OrderServices/"
#    headers = {
#        "Content-Type": "application/json"
#    }
#    print("URL set")
#    try:
#        response = requests.get(api_url, headers=headers)
#        response.raise_for_status()
#        records = response.json()
#        for record in records:
#            if customer.CustomerID == record['CustomerID']:
#                await patch_order_status(record['CustomerID'])
#    except requests.exceptions.RequestException as e:
#        raise HTTPException(status_code=response.status_code, detail=str(response.json))
    pass


# only needed for psycopg 3 - replace postgresql
# with postgresql+psycopg in settings.DATABASE_URL
connection_string = str(settings.DATABASE_URL).replace(
    "postgresql", "postgresql+psycopg"
)


# recycle connections after 5 minutes
# to correspond with the compute scale down
engine = create_engine(
    connection_string, connect_args={}, pool_recycle=300
)


def create_db_and_tables()->None:
    SQLModel.metadata.create_all(engine)


async def consume_messages(topic, bootstrap_servers):
    # Create a consumer instance.
    consumer = AIOKafkaConsumer(
        topic,
        bootstrap_servers=bootstrap_servers,
        group_id="customer-group",
        auto_offset_reset='earliest'
    )

    # Start the consumer.
    await consumer.start()
    try:
        # Continuously listen for messages.
        async for message in consumer:
            print(f"Customer Information received message: {message.value.decode()} on topic {message.topic}")
            # Here you can add code to process each message.
            # Example: parse the message, store it in a database, etc.
            if message.topic in ["DeleteCustomer", "UpdateCustomer", "ReplaceCustomer"]:
                message_dict = json.loads(message.value.decode())
                customer_info = CustomerInformation.model_validate(message_dict)
                await fetch_customer_orders(customer_info)
    finally:
        # Ensure to close the consumer when done.
        await consumer.stop()


# The first part of the function, before the yield, will
# be executed before the application starts.
# https://fastapi.tiangolo.com/advanced/events/#lifespan-function
# loop = asyncio.get_event_loop()
@asynccontextmanager
async def lifespan(app: FastAPI)-> AsyncGenerator[None, None]:
    print("Creating tables..")
#    loop.run_until_complete(consume_messages('todos', 'broker:19092'))

    task1 = asyncio.create_task(consume_messages('CreateCustomer', 'broker:19092'))
    task2 = asyncio.create_task(consume_messages('UpdateCustomer', 'broker:19092'))
    task3 = asyncio.create_task(consume_messages('ReplaceCustomer', 'broker:19092'))
    task4 = asyncio.create_task(consume_messages('DeleteCustomer', 'broker:19092'))

    create_db_and_tables()
    yield


app = FastAPI(lifespan=lifespan, title="Hello World API with DB", version="0.0.1",
    # servers=[
    #     {
    #         "url": "http://127.0.0.1:8000", # ADD NGROK URL Here Before Creating GPT Action
    #         "description": "Development Server"
    #     }
    #     ]
        )

def get_session():
    with Session(engine) as session:
        yield session


@app.get("/")
async def read_root():
    return {"Hello": "Ahmer Arman"}

# Kafka Producer as a dependency
async def get_kafka_producer():
    producer = AIOKafkaProducer(bootstrap_servers='broker:19092')
    await producer.start()
    try:
        yield producer
    finally:
        await producer.stop()

@app.post("/CustomerInformation/", response_model=CustomerInformation)
async def create_customer(CustInfo: CustomerInformation, session: Annotated[Session, Depends(get_session)], producer: Annotated[AIOKafkaProducer, Depends(get_kafka_producer)])->CustomerInformation:
    try:
        CustomerInformation_dict = {field: getattr(CustInfo, field) for field in CustInfo.model_dump()}
        CustomerInformation_json = json.dumps(CustomerInformation_dict).encode("utf-8")

        # Produce message
        await producer.send_and_wait("CreateCustomer", CustomerInformation_json)
        session.add(CustInfo)
        session.commit()
        session.refresh(CustInfo)
    except:
        raise HTTPException(status_code=500, detail="Invalid Data")
    return CustInfo


@app.get("/CustomerInformation/", response_model=list[CustomerInformation])
def read_customerInformation(session: Annotated[Session, Depends(get_session)]):
        customerInformation = session.exec(select(CustomerInformation)).all()
        return customerInformation


@app.get("/CustomerInformation/{customer_id}", response_model=CustomerInformation)
def read_one_customer(session: Annotated[Session, Depends(get_session)], customer_id: int):
        customerInformation = session.exec(select(CustomerInformation).where(CustomerInformation.CustomerID==customer_id)).first()
        if not customerInformation:
            raise HTTPException(status_code=404, detail="Customer not found.")
        return customerInformation


@app.patch("/CustomerInformation/{customer_id}", response_model=CustomerInformation)
async def update_customer(customer_id: int, customer_update: CustomerUpdate, session: Annotated[Session, Depends(get_session)], producer: Annotated[AIOKafkaProducer, Depends(get_kafka_producer)]):
        customer = session.get(CustomerInformation, customer_id)
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")

        update_data = customer_update.model_dump(exclude_unset=True)

        for key, value in update_data.items():
            setattr(customer, key, value)

        session.add(customer)
        session.commit()
        session.refresh(customer)

        # Produce message
        CustomerInformation_dict = {field: getattr(customer, field) for field in customer.model_dump()}
        CustomerInformation_json = json.dumps(CustomerInformation_dict).encode("utf-8")
        await producer.send_and_wait("UpdateCustomer", CustomerInformation_json)

        return customer


@app.put("/CustomerInformation/{customer_id}", response_model=CustomerInformation)
async def replace_customer(customer_id: int, customer_info: CustomerInformation, session: Annotated[Session, Depends(get_session)], producer: Annotated[AIOKafkaProducer, Depends(get_kafka_producer)]):
    existing_customer = session.get(CustomerInformation, customer_id)
    if not existing_customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    # Update the fields of the existing_vendor with the new data
    try:
        for key, value in customer_info.model_dump().items():
            setattr(existing_customer, key, value)

        session.add(existing_customer)
        session.commit()
        session.refresh(existing_customer)

        CustomerInformation_dict = {field: getattr(existing_customer, field) for field in existing_customer.model_dump()}
        CustomerInformation_json = json.dumps(CustomerInformation_dict).encode("utf-8")
        await producer.send_and_wait("ReplaceCustomer", CustomerInformation_json)
    except:
        raise HTTPException(status_code=422, detail="Invalid data.")

    return existing_customer


@app.delete("/CustomerInformation/{customer_id}", response_model=CustomerInformation)
async def delete_costomer(session: Annotated[Session, Depends(get_session)], producer: Annotated[AIOKafkaProducer, Depends(get_kafka_producer)], customer_id: int):
    try:
        customer = session.get(CustomerInformation, customer_id)
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")

        key = "Enabled"
        value = False
        setattr(customer, key, value)

        session.add(customer)
        session.commit()
        session.refresh(customer)

        # Produce message
        CustomerInformation_dict = {field: getattr(customer, field) for field in customer.model_dump()}
        CustomerInformation_json = json.dumps(CustomerInformation_dict).encode("utf-8")
        await producer.send_and_wait("DeleteCustomer", CustomerInformation_json)
    except:
        raise HTTPException(status_code=500, detail="Invalid data")
    return customer
