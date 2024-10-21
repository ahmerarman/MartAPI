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


class VendorInformation(SQLModel, table=True):
    VendorCode: Optional[int] = Field(default=None, primary_key=True)
    VendorName: str = Field(default=None, index=True, max_length=50)
    VendorAddress: str = Field(default=None, max_length=50)
    NTN_No: str = Field(default=None, max_length=20)
    STN_No: str = Field(default=None, max_length=20)
    ContactPerson: str = Field(default=None, max_length=20)
    Contact_No: str = Field(default=None, max_length=20)
    Email: str = Field(default=None, max_length=20)
    Enabled: bool = Field(default=True)
    BankAC_No: str = Field(default=None, max_length=25)


class VendorUpdate(SQLModel):
    VendorName: str | None = None
    VendorAddress: str | None = None
    NTN_No: str | None = None
    STN_No: str | None = None
    ContactPerson: str | None = None
    Contact_No: str | None = None
    Email: str | None = None
    Enabled: bool | None = None
    BankAC_No: str | None = None


async def patch_inventory_status(record_id: int, enabled: bool):
    api_url = f"http://api5:8000/inventory/{record_id}"
    headers = {
        "Content-Type": "application/json"
    }
    data = {
        "Enabled": enabled
    }
    try:
        response = requests.patch(api_url, headers=headers, json=data)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=response.status_code, detail=str(e))


async def fetch_vendor_inventories(vendor: VendorInformation):
    api_url = f"http://api5:8000/inventory/"
    headers = {
        "Content-Type": "application/json"
    }
    print("URL set")
    try:
        response = requests.get(api_url, headers=headers)
        response.raise_for_status()
        records = response.json()
        for record in records:
            if vendor.VendorCode == record['VendorID']:
                await patch_inventory_status(record['id'], vendor.Enabled)
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=response.status_code, detail=str(response.json))


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
        group_id="vendor-group",
        auto_offset_reset='earliest'
    )

    # Start the consumer.
    await consumer.start()
    try:
        # Continuously listen for messages.
        async for message in consumer:
            print(f"Vendor Information received message: {message.value.decode()} on topic {message.topic}")
            # Here you can add code to process each message.
            # Example: parse the message, store it in a database, etc.
            if message.topic in ["DeleteVendor", "UpdateVendor", "ReplaceVendor"]:
                message_dict = json.loads(message.value.decode())
                vendor_info = VendorInformation.model_validate(message_dict)
                await fetch_vendor_inventories(vendor_info)
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

    task1 = asyncio.create_task(consume_messages('CreateVendor', 'broker:19092'))
    task2 = asyncio.create_task(consume_messages('UpdateVendor', 'broker:19092'))
    task3 = asyncio.create_task(consume_messages('ReplaceVendor', 'broker:19092'))
    task4 = asyncio.create_task(consume_messages('DeleteVendor', 'broker:19092'))

    create_db_and_tables()
    yield


app = FastAPI(lifespan=lifespan, title="Hello World API with DB", 
    version="0.0.1",
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

@app.post("/VendorInformation/", response_model=VendorInformation)
async def create_vendor(VendInfo: VendorInformation, session: Annotated[Session, Depends(get_session)], producer: Annotated[AIOKafkaProducer, Depends(get_kafka_producer)])->VendorInformation:
    try:
        VendorInformation_dict = {field: getattr(VendInfo, field) for field in VendInfo.model_dump()}
        VendorInformation_json = json.dumps(VendorInformation_dict).encode("utf-8")

        # Produce message
        await producer.send_and_wait("CreateVendor", VendorInformation_json)
        session.add(VendInfo)
        session.commit()
        session.refresh(VendInfo)
    except:
        raise HTTPException(status_code=500, detail="Invalid Data")
    return VendInfo


@app.get("/VendorInformation/", response_model=list[VendorInformation])
def read_venderInformation(session: Annotated[Session, Depends(get_session)]):
        venderInformation = session.exec(select(VendorInformation).where(VendorInformation.Enabled==True)).all()
        return venderInformation


@app.get("/VendorInformation/{vendor_id}", response_model=VendorInformation)
def read_one_vend(session: Annotated[Session, Depends(get_session)], vendor_id: int):
        venderInformation = session.exec(select(VendorInformation).where(VendorInformation.VendorCode==vendor_id, VendorInformation.Enabled==True)).first()
        if not venderInformation:
            raise HTTPException(status_code=404, detail="Vendor not found.")
        return venderInformation


@app.patch("/VendorInformation/{vendor_id}", response_model=VendorInformation)
async def update_vendor(vendor_id: int, vendor_update: VendorUpdate, session: Annotated[Session, Depends(get_session)], producer: Annotated[AIOKafkaProducer, Depends(get_kafka_producer)]):
        vendor = session.get(VendorInformation, vendor_id)
        if not vendor:
            raise HTTPException(status_code=404, detail="Vendor not found")

        update_data = vendor_update.model_dump(exclude_unset=True)

        for key, value in update_data.items():
            setattr(vendor, key, value)

        session.add(vendor)
        session.commit()
        session.refresh(vendor)

        # Produce message
        VendorInformation_dict = {field: getattr(vendor, field) for field in vendor.model_dump()}
        VendorInformation_json = json.dumps(VendorInformation_dict).encode("utf-8")
        await producer.send_and_wait("UpdateVendor", VendorInformation_json)

        return vendor


@app.put("/VendorInformation/{vendor_id}", response_model=VendorInformation)
async def replace_vendor(vendor_id: int, vend_info: VendorInformation, session: Annotated[Session, Depends(get_session)], producer: Annotated[AIOKafkaProducer, Depends(get_kafka_producer)]):
    existing_vendor = session.get(VendorInformation, vendor_id)
    if not existing_vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    # Update the fields of the existing_vendor with the new data
    try:
        for key, value in vend_info.model_dump().items():
            setattr(existing_vendor, key, value)

        session.add(existing_vendor)
        session.commit()
        session.refresh(existing_vendor)

        VendorInformation_dict = {field: getattr(existing_vendor, field) for field in existing_vendor.model_dump()}
        VendorInformation_json = json.dumps(VendorInformation_dict).encode("utf-8")
        await producer.send_and_wait("ReplaceVendor", VendorInformation_json)
    except:
        raise HTTPException(status_code=422, detail="Invalid data.")

    return existing_vendor


@app.delete("/VendorInformation/{vendor_id}", response_model=VendorInformation)
async def delete_vendor(session: Annotated[Session, Depends(get_session)], producer: Annotated[AIOKafkaProducer, Depends(get_kafka_producer)], vendor_id: int):
    try:
        vendor = session.get(VendorInformation, vendor_id)
        if not vendor:
            raise HTTPException(status_code=404, detail="Vendor not found")

        key = "Enabled"
        value = False
        setattr(vendor, key, value)

        session.add(vendor)
        session.commit()
        session.refresh(vendor)

        # Produce message
        VendorInformation_dict = {field: getattr(vendor, field) for field in vendor.model_dump()}
        VendorInformation_json = json.dumps(VendorInformation_dict).encode("utf-8")
        await producer.send_and_wait("DeleteVendor", VendorInformation_json)
    except:
        raise HTTPException(status_code=500, detail="Invalid data")
    return vendor
