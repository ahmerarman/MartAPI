import json
import requests # type: ignore
from typing import Annotated
from sqlmodel import Session, select
from app.db import get_session
from inventory.model.database import Inventory
from fastapi import APIRouter, HTTPException, Query, Depends
from datetime import datetime
from inventory.schemas.schemas import InventoryCreate, InventoryRead, InventoryUpdate, InventoryUpdateComplete
from aiokafka import AIOKafkaProducer # type: ignore

inventory_router = APIRouter(prefix="/inventory", tags=["inventory"])

# Serialization function for datetime object serialization for KAFKA messaging
# Convert datetime object to string
def json_serializer(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")

async def fetch_product(id: int):
    api_url = f"http://api4:8000/products/{id}"
    headers = {
        "Content-Type": "application/json"
    }
    try:
        response = requests.get(api_url, headers=headers)
        response.raise_for_status()
        return response.json
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=response.status_code, detail=str(response.json))

async def fetch_vendor(id: int):
    api_url = f"http://api3:8000/VendorInformation/{id}"
    headers = {
        "Content-Type": "application/json"
    }
    try:
        response = requests.get(api_url, headers=headers)
        response.raise_for_status()
        return response.json
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=response.status_code, detail=str(response.json))

async def get_kafka_producer():
    producer = AIOKafkaProducer(bootstrap_servers='broker:19092')
    await producer.start()
    try:
        yield producer
    finally:
        await producer.stop()

@inventory_router.post("/", response_model=InventoryRead)
async def create_inventory(InventoryInfo: InventoryCreate, session: Annotated[Session, Depends(get_session)], producer: Annotated[AIOKafkaProducer, Depends(get_kafka_producer)]):
    try:
        InventoryInformation_dict = {field: getattr(InventoryInfo, field) for field in InventoryInfo.model_dump()}
        InventoryInformation_json = json.dumps(InventoryInformation_dict, default=json_serializer).encode("utf-8")
        id = InventoryInfo.ProductID
        product = await fetch_product(id)

        id = InventoryInfo.VendorID
        vendor = await fetch_vendor(id)

        # Produce message
        await producer.send_and_wait("Inventory", InventoryInformation_json)

        db_inventory = Inventory.model_validate(InventoryInfo)
        session.add(db_inventory)
        session.commit()
        session.refresh(db_inventory)

    except:
        raise HTTPException(status_code=500, detail="Invalid Data")
    return db_inventory

@inventory_router.get("/", response_model=list[InventoryRead])
async def read_inventories(session: Annotated[Session, Depends(get_session)], offset: int = 0, limit: int = Query(default=100, le=100)):
    inventories = session.exec(select(Inventory).offset(offset).limit(limit)).all()
    return inventories

@inventory_router.get("/{id}", response_model=InventoryRead)
async def read_inventory(session: Annotated[Session, Depends(get_session)], id: int):
    inventory = session.exec(select(Inventory).where(Inventory.id == id, Inventory.Enabled == True)).first()
    if not inventory:
        raise HTTPException(status_code=404, detail="Record not found")
    return inventory

@inventory_router.patch("/{id}", response_model=InventoryRead)
async def update_inventory(session: Annotated[Session, Depends(get_session)], producer: Annotated[AIOKafkaProducer, Depends(get_kafka_producer)], id: int, InventoryInfo: InventoryUpdate):
    try:
        db_inventory = session.get(Inventory, id)

        if not db_inventory:
            raise HTTPException(status_code=404, detail="Record not found.")
        inventory_data = InventoryInfo.model_dump(exclude_unset=True)
        for key, value in inventory_data.items():
            setattr(db_inventory, key, value)
        session.add(db_inventory)
        session.commit()
        session.refresh(db_inventory)

        InventoryInformation_dict = {field: getattr(InventoryInfo, field) for field in InventoryInfo.model_dump()}
        InventoryInformation_json = json.dumps(InventoryInformation_dict, default=json_serializer).encode("utf-8")
        # Produce message
        await producer.send_and_wait("Inventory", InventoryInformation_json)
    except:
        raise HTTPException(status_code=500, detail="Invalid data")
    return db_inventory

@inventory_router.put("/{id}", response_model=InventoryRead)
async def replace_inventory(session: Annotated[Session, Depends(get_session)], producer: Annotated[AIOKafkaProducer, Depends(get_kafka_producer)], id: int, InventoryInfo: InventoryUpdateComplete):
    try:
        db_inventory = session.get(Inventory, id)
        if not db_inventory:
            raise HTTPException(status_code=404, detail="Record not found.")
        inventory_data = InventoryInfo.model_dump()
        for key, value in inventory_data.items():
            setattr(db_inventory, key, value)
        session.add(db_inventory)
        session.commit()
        session.refresh(db_inventory)

        InventoryInformation_dict = {field: getattr(InventoryInfo, field) for field in InventoryInfo.model_dump()}
        InventoryInformation_json = json.dumps(InventoryInformation_dict, default=json_serializer).encode("utf-8")
        # Produce message
        await producer.send_and_wait("Inventory", InventoryInformation_json)
    except:
        raise HTTPException(status_code=500, detail="Invalid data")
    return db_inventory

@inventory_router.delete("/{id}", response_model=InventoryRead)
async def delete_inventory(session: Annotated[Session, Depends(get_session)], producer2: Annotated[AIOKafkaProducer, Depends(get_kafka_producer)], id: int):
    try:
        db_inventory = session.get(Inventory, id)
        if not db_inventory:
            raise HTTPException(status_code=404, detail="Record not found.")
        key = "Enabled"
        value = False
        setattr(db_inventory, key, value)
        session.add(db_inventory)
        session.commit()
        session.refresh(db_inventory)

        InventoryInformation_dict = {field: getattr(db_inventory, field) for field in db_inventory.model_dump()}
        InventoryInformation_json = json.dumps(InventoryInformation_dict, default=json_serializer).encode("utf-8")
        # Produce message
        await producer2.send_and_wait("Inventory", InventoryInformation_json)
    except:
        raise HTTPException(status_code=500, detail="Invalid Data")
    return db_inventory
