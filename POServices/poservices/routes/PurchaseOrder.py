import json
from typing import Annotated
from sqlmodel import Session, select
from app.db import get_session
from poservices.model.database import POTable
from fastapi import APIRouter, HTTPException, Query, Depends
from poservices.schemas.schemas import POCreate, PORead, POUpdate, POUpdateComplete, POReadWithLineItem
from aiokafka import AIOKafkaProducer # type: ignore
from datetime import datetime

po_router = APIRouter(prefix="/poservices", tags=["poservices"])

# Serialization function for datetime object serialization for KAFKA messaging
# Convert datetime object to string
def json_serializer(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")

async def get_kafka_producer():
    producer2 = AIOKafkaProducer(bootstrap_servers='broker:19092')
    await producer2.start()
    try:
        yield producer2
    finally:
        await producer2.stop()

@po_router.post("/", response_model=PORead)
async def create_po(POInfo: POCreate, session: Annotated[Session, Depends(get_session)], producer2: Annotated[AIOKafkaProducer, Depends(get_kafka_producer)]):
    try:
        # Produce message
        PurchaseOrderInformation_dict = {field: getattr(POInfo, field) for field in POInfo.model_dump()}
        PurchaseOrderInformation_json = json.dumps(PurchaseOrderInformation_dict, default=json_serializer).encode("utf-8")
        await producer2.send_and_wait("CreatePO", PurchaseOrderInformation_json)

        db_po = POTable.model_validate(POInfo)
        session.add(db_po)
        session.commit()
        session.refresh(db_po)
    except:
        raise HTTPException(status_code=500, detail="Invalid Data")
    return db_po

@po_router.get("/", response_model=list[POReadWithLineItem])
async def read_pos(session: Annotated[Session, Depends(get_session)], offset: int = 0, limit: int = Query(default=100, le=100)):
    pos = session.exec(select(POTable).offset(offset).limit(limit)).all()
    return pos

@po_router.get("/{id}", response_model=POReadWithLineItem)
async def read_po(session: Annotated[Session, Depends(get_session)], id: int):
    po = session.exec(select(POTable).where(POTable.id == id)).first()
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    return po

@po_router.patch("/{id}", response_model=PORead)
async def update_po(session: Annotated[Session, Depends(get_session)], producer2: Annotated[AIOKafkaProducer, Depends(get_kafka_producer)], po_id: int, POInfo: POUpdate):
    try:
        db_po = session.exec(select(POTable).where(POTable.id == po_id)).first()
        if not db_po:
            raise HTTPException(status_code=404, detail="Purchase order not found.")
        po_data = POInfo.model_dump(exclude_unset=True)
        for key, value in po_data.items():
            setattr(db_po, key, value)
        session.add(db_po)
        session.commit()
        session.refresh(db_po)

        PurchaseOrderInformation_dict = {field: getattr(db_po, field) for field in db_po.model_dump()}
        PurchaseOrderInformation_json = json.dumps(PurchaseOrderInformation_dict, default=json_serializer).encode("utf-8")
        # Produce message
        await producer2.send_and_wait("UpdatePO", PurchaseOrderInformation_json)
    except:
        raise HTTPException(status_code=500, detail="Invalid Data")
    return db_po

@po_router.put("/{id}", response_model=PORead)
async def replace_po(session: Annotated[Session, Depends(get_session)], producer2: Annotated[AIOKafkaProducer, Depends(get_kafka_producer)], po_id: int, POInfo: POUpdateComplete):
    try:
        db_po = session.exec(select(POTable).where(POTable.id == po_id)).first()
        if not db_po:
            raise HTTPException(status_code=404, detail="Purchase order not found.")
        po_data = POInfo.model_dump()
        for key, value in po_data.items():
            setattr(db_po, key, value)
        session.add(db_po)
        session.commit()
        session.refresh(db_po)

        PurchaseOrderInformation_dict = {field: getattr(db_po, field) for field in db_po.model_dump()}
        PurchaseOrderInformation_json = json.dumps(PurchaseOrderInformation_dict, default=json_serializer).encode("utf-8")
        # Produce message
        await producer2.send_and_wait("ReplacePO", PurchaseOrderInformation_json)
    except:
        raise HTTPException(status_code=500, detail="Invalid Data")
    return db_po

@po_router.delete("/{id}", response_model=PORead)
async def delete_po(session: Annotated[Session, Depends(get_session)], producer2: Annotated[AIOKafkaProducer, Depends(get_kafka_producer)], po_id: int):
    try:
        db_po = session.exec(select(POTable).where(POTable.id == po_id)).first()
        if not db_po:
            raise HTTPException(status_code=404, detail="Purchase order not found.")
        session.delete(db_po)
        session.commit()
#        session.refresh(db_product)

        PurchaseOrderInformation_dict = {field: getattr(db_po, field) for field in db_po.model_dump()}
        PurchaseOrderInformation_json = json.dumps(PurchaseOrderInformation_dict, default=json_serializer).encode("utf-8")
        # Produce message
        await producer2.send_and_wait("DeletePO", PurchaseOrderInformation_json)
    except:
        raise HTTPException(status_code=500, detail="Invalid Data")
    return db_po
