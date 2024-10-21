import json
from typing import Annotated
from sqlmodel import Session, select
from app.db import get_session
from orderservices.model.database import OrderTable
from fastapi import APIRouter, HTTPException, Query, Depends
from orderservices.schemas.schemas import OrderCreate, OrderRead, OrderUpdate, OrderUpdateComplete, OrderReadWithLineItem
from aiokafka import AIOKafkaProducer # type: ignore
from datetime import datetime

order_router = APIRouter(prefix="/orderservies", tags=["orderservices"])

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

@order_router.post("/", response_model=OrderRead)
async def create_order(OrderInfo: OrderCreate, session: Annotated[Session, Depends(get_session)], producer2: Annotated[AIOKafkaProducer, Depends(get_kafka_producer)]):
    try:
        # Produce message
        OrderInformation_dict = {field: getattr(OrderInfo, field) for field in OrderInfo.model_dump()}
        OrderInformation_json = json.dumps(OrderInformation_dict, default=json_serializer).encode("utf-8")

        db_order = OrderTable.model_validate(OrderInfo)
        session.add(db_order)
        session.commit()
        session.refresh(db_order)
        await producer2.send_and_wait("CreateOrder", OrderInformation_json)
    except:
        raise HTTPException(status_code=500, detail="Invalid Data")
    return db_order

@order_router.get("/", response_model=list[OrderReadWithLineItem])
async def read_orders(session: Annotated[Session, Depends(get_session)], offset: int = 0, limit: int = Query(default=100, le=100)):
    orders = session.exec(select(OrderTable).offset(offset).limit(limit)).all()
    return orders

@order_router.get("/{id}", response_model=OrderReadWithLineItem)
async def read_order(session: Annotated[Session, Depends(get_session)], id: int):
    order = session.get(OrderTable, id)
#    order = session.exec(select(OrderTable).where(OrderTable.id == id)).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order

@order_router.patch("/{id}", response_model=OrderRead)
async def update_order(session: Annotated[Session, Depends(get_session)], producer2: Annotated[AIOKafkaProducer, Depends(get_kafka_producer)], order_id: int, OrderInfo: OrderUpdate):
    try:
        db_order = session.exec(select(OrderTable).where(OrderTable.id == order_id, OrderTable.EnableEdit == True)).first()
        if not db_order:
            raise HTTPException(status_code=404, detail="Order not found.")
        order_data = OrderInfo.model_dump(exclude_unset=True)
        for key, value in order_data.items():
            setattr(db_order, key, value)
        session.add(db_order)
        session.commit()
        session.refresh(db_order)

        OrderInformation_dict = {field: getattr(db_order, field) for field in db_order.model_dump()}
        OrderInformation_json = json.dumps(OrderInformation_dict, default=json_serializer).encode("utf-8")
        # Produce message
        await producer2.send_and_wait("UpdateOrder", OrderInformation_json)
    except:
        raise HTTPException(status_code=500, detail="Invalid Data")
    return db_order

@order_router.put("/{id}", response_model=OrderRead)
async def replace_order(session: Annotated[Session, Depends(get_session)], producer2: Annotated[AIOKafkaProducer, Depends(get_kafka_producer)], order_id: int, OrderInfo: OrderUpdateComplete):
    try:
        db_order = session.exec(select(OrderTable).where(OrderTable.id == order_id, OrderTable.EnableEdit == True)).first()
        if not db_order:
            raise HTTPException(status_code=404, detail="Order not found.")
        order_data = OrderInfo.model_dump()
        for key, value in order_data.items():
            setattr(db_order, key, value)
        session.add(db_order)
        session.commit()
        session.refresh(db_order)

        OrderInformation_dict = {field: getattr(db_order, field) for field in db_order.model_dump()}
        OrderInformation_json = json.dumps(OrderInformation_dict, default=json_serializer).encode("utf-8")
        # Produce message
        await producer2.send_and_wait("ReplaceOrder", OrderInformation_json)
    except:
        raise HTTPException(status_code=500, detail="Invalid Data")
    return db_order

@order_router.delete("/{id}", response_model=OrderRead)
async def delete_order(session: Annotated[Session, Depends(get_session)], producer2: Annotated[AIOKafkaProducer, Depends(get_kafka_producer)], order_id: int):
    try:
        db_order = session.exec(select(OrderTable).where(OrderTable.id == order_id, OrderTable.EnableEdit == True)).first()
        if not db_order:
            raise HTTPException(status_code=404, detail="Order not found.")
        session.delete(db_order)
        session.commit()
#        session.refresh(db_product)

        OrderInformation_dict = {field: getattr(db_order, field) for field in db_order.model_dump()}
        OrderInformation_json = json.dumps(OrderInformation_dict, default=json_serializer).encode("utf-8")
        # Produce message
        await producer2.send_and_wait("DeleteOrder", OrderInformation_json)
    except:
        raise HTTPException(status_code=500, detail="Invalid Data")
    return db_order
