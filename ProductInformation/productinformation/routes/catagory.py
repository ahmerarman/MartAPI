import json
from typing import Annotated
from sqlmodel import Session, select
from app.db import get_session
from productinformation.model.database import ProductCatagory
from fastapi import APIRouter, HTTPException, Query, Depends
from productinformation.schemas.schemas import CatagoryCreate, CatagoryRead, CatagoryReadWithProduct, CatagoryUpdate, CatagoryUpdateComplete
from aiokafka import AIOKafkaProducer # type: ignore

catagory_router = APIRouter(prefix="/catagory", tags=["catagory"])

async def get_kafka_producer():
    producer = AIOKafkaProducer(bootstrap_servers='broker:19092')
    await producer.start()
    try:
        yield producer
    finally:
        await producer.stop()

@catagory_router.post("/", response_model=CatagoryRead)
async def create_catagory(CatagoryInfo: CatagoryCreate, session: Annotated[Session, Depends(get_session)], producer: Annotated[AIOKafkaProducer, Depends(get_kafka_producer)]):
    try:
        db_catagory = ProductCatagory.model_validate(CatagoryInfo)
        session.add(db_catagory)
        session.commit()
        session.refresh(db_catagory)

        CatagoryInformation_dict = {field: getattr(CatagoryInfo, field) for field in CatagoryInfo.model_dump()}
        CatagoryInformation_json = json.dumps(CatagoryInformation_dict).encode("utf-8")
        # Produce message
        await producer.send_and_wait("Catagory", CatagoryInformation_json)
    except:
        raise HTTPException(status_code=500, detail="Invalid Data")
    return db_catagory

@catagory_router.get("/", response_model=list[CatagoryReadWithProduct])
async def read_catagories(session: Annotated[Session, Depends(get_session)], offset: int = 0, limit: int = Query(default=100, le=100)):
    catagories = session.exec(select(ProductCatagory).offset(offset).limit(limit)).all()
    return catagories

@catagory_router.get("/{catagory_id}", response_model=CatagoryReadWithProduct)
async def read_catagory(session: Annotated[Session, Depends(get_session)], catagory_id: int):
    catagory = session.get(ProductCatagory, catagory_id)
    if not catagory:
        raise HTTPException(status_code=404, detail="Catagory not found")
    return catagory

@catagory_router.patch("/{catagory_id}", response_model=CatagoryRead)
async def update_catagory(session: Annotated[Session, Depends(get_session)], producer: Annotated[AIOKafkaProducer, Depends(get_kafka_producer)], catagory_id: int, CatagoryInfo: CatagoryUpdate):
    try:
        db_catagory = session.get(ProductCatagory, catagory_id)
        if not db_catagory:
            raise HTTPException(status_code=404, detail="Catagory not found.")
        catagory_data = CatagoryInfo.model_dump(exclude_unset=True)
        for key, value in catagory_data.items():
            setattr(db_catagory, key, value)
        session.add(db_catagory)
        session.commit()
        session.refresh(db_catagory)

        CatagoryInformation_dict = {field: getattr(db_catagory, field) for field in db_catagory.model_dump()}
        CatagoryInformation_json = json.dumps(CatagoryInformation_dict).encode("utf-8")
        # Produce message
        await producer.send_and_wait("Catagory", CatagoryInformation_json)
    except:
        raise HTTPException(status_code=500, detail="Invalid data")
    return db_catagory

@catagory_router.put("/{catagory_id}", response_model=CatagoryRead)
async def replace_catagory(session: Annotated[Session, Depends(get_session)], producer: Annotated[AIOKafkaProducer, Depends(get_kafka_producer)], catagory_id: int, CatagoryInfo: CatagoryUpdateComplete):
    try:
        db_catagory = session.get(ProductCatagory, catagory_id)
        if not db_catagory:
            raise HTTPException(status_code=404, detail="Catagory not found.")
        catagory_data = CatagoryInfo.model_dump()
        for key, value in catagory_data.items():
            setattr(db_catagory, key, value)
        session.add(db_catagory)
        session.commit()
        session.refresh(db_catagory)

        CatagoryInformation_dict = {field: getattr(db_catagory, field) for field in db_catagory.model_dump()}
        CatagoryInformation_json = json.dumps(CatagoryInformation_dict).encode("utf-8")
        # Produce message
        await producer.send_and_wait("Catagory", CatagoryInformation_json)
    except:
        raise HTTPException(status_code=500, detail="Invalid data")
    return db_catagory

@catagory_router.delete("/{catagory_id}", response_model=CatagoryRead)
async def delete_catagory(session: Annotated[Session, Depends(get_session)], producer: Annotated[AIOKafkaProducer, Depends(get_kafka_producer)], catagory_id: int):
    try:
        db_catagory = session.get(ProductCatagory, catagory_id)
        if not db_catagory:
            raise HTTPException(status_code=404, detail="Catagory not found.")
        session.delete(db_catagory)
        session.commit()
#        session.refresh(db_catagory)

        CatagoryInformation_dict = {field: getattr(db_catagory, field) for field in db_catagory.model_dump()}
        CatagoryInformation_json = json.dumps(CatagoryInformation_dict).encode("utf-8")
        # Produce message
        await producer.send_and_wait("Catagory", CatagoryInformation_json)
    except:
        raise HTTPException(status_code=500, detail="Invalid data")
    return db_catagory
