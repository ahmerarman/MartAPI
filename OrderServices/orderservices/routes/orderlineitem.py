import json
from typing import Annotated
import requests # type: ignore
from sqlmodel import Session, select
from app.db import get_session
from orderservices.model.database import OrderLineItem, OrderTable
from fastapi import APIRouter, HTTPException, Query, Depends
from orderservices.schemas.schemas import OrderLineItemCreate, OrderLineItemRead, OrderLineItemReadWithOrder, OrderLineItemUpdate, OrderLineItemUpdateComplete
from aiokafka import AIOKafkaProducer # type: ignore

orderlineitem_router = APIRouter(prefix="/orderlineitem", tags=["orderlineitem"])

async def get_kafka_producer():
    producer = AIOKafkaProducer(bootstrap_servers='broker:19092')
    await producer.start()
    try:
        yield producer
    finally:
        await producer.stop()

async def fetch_product_inventories(id: int):
    api_url = f"http://api5:8000/inventory/{id}"
    headers = {
        "Content-Type": "application/json"
    }
    try:
        response = requests.get(api_url, headers=headers)
        response.raise_for_status()
        records = response.json()
        return records
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=response.status_code, detail=str(response.json))

@orderlineitem_router.post("/", response_model=OrderLineItemRead)
async def create_orderlineitem(OrderLineItemInfo: OrderLineItemCreate, session: Annotated[Session, Depends(get_session)], producer: Annotated[AIOKafkaProducer, Depends(get_kafka_producer)]):
    try:
        order = session.exec(select(OrderTable).where(OrderTable.id==OrderLineItemInfo.OrderID, OrderTable.EnableEdit==True)).first()
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        inventory = await fetch_product_inventories(OrderLineItemInfo.ProductID)
        if inventory['Quantity']<OrderLineItemInfo.Quantity:
            raise HTTPException(status_code=500, detail="Invalid quantity.")

        db_orderlineitem = OrderLineItem.model_validate(OrderLineItemInfo)
        session.add(db_orderlineitem)
        session.commit()
        session.refresh(db_orderlineitem)

        OrderLineItemInformation_dict = {field: getattr(OrderLineItemInfo, field) for field in OrderLineItemInfo.model_dump()}
        OrderLineItemInformation_json = json.dumps(OrderLineItemInformation_dict).encode("utf-8")
        # Produce message
        await producer.send_and_wait("CreateOrderLineItem", OrderLineItemInformation_json)
    except:
        raise HTTPException(status_code=500, detail="Invalid Data")
    return db_orderlineitem

@orderlineitem_router.get("/", response_model=list[OrderLineItemReadWithOrder])
async def read_orderlineitems(session: Annotated[Session, Depends(get_session)], offset: int = 0, limit: int = Query(default=100, le=100)):
    orderlineitems = session.exec(select(OrderLineItem).offset(offset).limit(limit)).all()
    return orderlineitems

@orderlineitem_router.get("/{id}", response_model=OrderLineItemReadWithOrder)
async def read_orderlineitem(session: Annotated[Session, Depends(get_session)], orderlineitem_id: int):
    orderlineitem = session.get(OrderLineItem, orderlineitem_id)
    if not orderlineitem:
        raise HTTPException(status_code=404, detail="Order line item not found")
    return orderlineitem

@orderlineitem_router.patch("/{id}", response_model=OrderLineItemRead)
async def update_orderlineitem(session: Annotated[Session, Depends(get_session)], producer: Annotated[AIOKafkaProducer, Depends(get_kafka_producer)], orderlineitem_id: int, OrderLineItemInfo: OrderLineItemUpdate):
    try:
        order = session.exec(select(OrderTable).where(OrderTable.id==OrderLineItemInfo.OrderID, OrderTable.EnableEdit==True)).first()
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

        db_orderlineitem = session.get(OrderLineItem, orderlineitem_id)
        if not db_orderlineitem:
            raise HTTPException(status_code=404, detail="Order line item not found.")

        if db_orderlineitem.Quantity!=OrderLineItemInfo.Quantity:
            inventory = await fetch_product_inventories(db_orderlineitem.ProductID)
            if inventory['Quantity']<OrderLineItemInfo.Quantity:
                raise HTTPException(status_code=500, detail="Invalid quantity.")

        orderlineitem_data = OrderLineItemInfo.model_dump(exclude_unset=True)
        for key, value in orderlineitem_data.items():
            setattr(db_orderlineitem, key, value)
        session.add(db_orderlineitem)
        session.commit()
        session.refresh(db_orderlineitem)

        OrderLineItemInformation_dict = {field: getattr(db_orderlineitem, field) for field in db_orderlineitem.model_dump()}
        OrderLineItemInformation_json = json.dumps(OrderLineItemInformation_dict).encode("utf-8")
        # Produce message
        await producer.send_and_wait("UpdateOrderLineItem", OrderLineItemInformation_json)
    except:
        raise HTTPException(status_code=500, detail="Invalid data")
    return db_orderlineitem

@orderlineitem_router.put("/{id}", response_model=OrderLineItemRead)
async def replace_orderlineitem(session: Annotated[Session, Depends(get_session)], producer: Annotated[AIOKafkaProducer, Depends(get_kafka_producer)], orderlineitem_id: int, OrderLineItemInfo: OrderLineItemUpdateComplete):
    try:
        order = session.exec(select(OrderTable).where(OrderTable.id==OrderLineItemInfo.OrderID, OrderTable.EnableEdit==True)).first()
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        inventory = await fetch_product_inventories(OrderLineItemInfo.ProductID)
        if inventory['Quantity']<OrderLineItemInfo.Quantity:
            raise HTTPException(status_code=500, detail="Invalid quantity.")

        db_orderlineitem = session.get(OrderLineItem, orderlineitem_id)
        if not db_orderlineitem:
            raise HTTPException(status_code=404, detail="Order line item not found.")
        orderlineitem_data = OrderLineItemInfo.model_dump()
        for key, value in orderlineitem_data.items():
            setattr(db_orderlineitem, key, value)
        session.add(db_orderlineitem)
        session.commit()
        session.refresh(db_orderlineitem)

        OrderLineItemInformation_dict = {field: getattr(db_orderlineitem, field) for field in db_orderlineitem.model_dump()}
        OrderLineItemInformation_json = json.dumps(OrderLineItemInformation_dict).encode("utf-8")
        # Produce message
        await producer.send_and_wait("ReplaceOrderLineItem", OrderLineItemInformation_json)
    except:
        raise HTTPException(status_code=500, detail="Invalid data")
    return db_orderlineitem

@orderlineitem_router.delete("/{id}", response_model=OrderLineItemRead)
async def delete_orderlineitem(session: Annotated[Session, Depends(get_session)], producer: Annotated[AIOKafkaProducer, Depends(get_kafka_producer)], orderlineitem_id: int):
    try:
        db_orderlineitem = session.get(OrderLineItem, orderlineitem_id)
        order = session.exec(select(OrderTable).where(OrderTable.id==orderlineitem_id, OrderTable.EnableEdit==True)).first()
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

        if not db_orderlineitem:
            raise HTTPException(status_code=404, detail="Order line item not found.")
        session.delete(db_orderlineitem)
        session.commit()
#        session.refresh(db_orderlineitem)

        OrderLineItemInformation_dict = {field: getattr(db_orderlineitem, field) for field in db_orderlineitem.model_dump()}
        OrderLineItemInformation_json = json.dumps(OrderLineItemInformation_dict).encode("utf-8")
        # Produce message
        await producer.send_and_wait("DeleteOrderLineItem", OrderLineItemInformation_json)
    except:
        raise HTTPException(status_code=500, detail="Invalid data")
    return db_orderlineitem
