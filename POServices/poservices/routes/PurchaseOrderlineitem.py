import json
from typing import Annotated
import requests # type: ignore
from sqlmodel import Session, select
from app.db import get_session
from poservices.model.database import POLineItem, POTable
from fastapi import APIRouter, HTTPException, Query, Depends
from poservices.schemas.schemas import POLineItemCreate, POLineItemRead, POLineItemReadWithPO, POLineItemUpdate, POLineItemUpdateComplete
from aiokafka import AIOKafkaProducer # type: ignore

polineitem_router = APIRouter(prefix="/polineitem", tags=["polineitem"])

async def get_kafka_producer():
    producer = AIOKafkaProducer(bootstrap_servers='broker:19092')
    await producer.start()
    try:
        yield producer
    finally:
        await producer.stop()

async def fetch_product_inventories(id: int):
#    api_url = f"http://api5:8000/inventory/{id}"
#    headers = {
#        "Content-Type": "application/json"
#    }
#    try:
#        response = requests.get(api_url, headers=headers)
#        response.raise_for_status()
#        records = response.json()
#        return records
#    except requests.exceptions.RequestException as e:
#        raise HTTPException(status_code=response.status_code, detail=str(response.json))
    pass

@polineitem_router.post("/", response_model=POLineItemRead)
async def create_polineitem(POLineItemInfo: POLineItemCreate, session: Annotated[Session, Depends(get_session)], producer: Annotated[AIOKafkaProducer, Depends(get_kafka_producer)]):
    try:
        po = session.exec(select(POTable).where(POTable.id==POLineItemInfo.PO_NO)).first()
        if not po:
            raise HTTPException(status_code=404, detail="Purchase order not found")
        inventory = await fetch_product_inventories(POLineItemInfo.ProductID)
        # if inventory['Quantity']<OrderLineItemInfo.Quantity:
        #     raise HTTPException(status_code=500, detail="Invalid quantity.")

        db_polineitem = POLineItem.model_validate(POLineItemInfo)
        session.add(db_polineitem)
        session.commit()
        session.refresh(db_polineitem)

        PurchaseOrderLineItemInformation_dict = {field: getattr(POLineItemInfo, field) for field in POLineItemInfo.model_dump()}
        PurchaseOrderLineItemInformation_json = json.dumps(PurchaseOrderLineItemInformation_dict).encode("utf-8")
        # Produce message
        await producer.send_and_wait("CreatePOLineItem", PurchaseOrderLineItemInformation_json)
    except:
        raise HTTPException(status_code=500, detail="Invalid Data")
    return db_polineitem

@polineitem_router.get("/", response_model=list[POLineItemReadWithPO])
async def read_polineitems(session: Annotated[Session, Depends(get_session)], offset: int = 0, limit: int = Query(default=100, le=100)):
    polineitems = session.exec(select(POLineItem).offset(offset).limit(limit)).all()
    return polineitems

@polineitem_router.get("/{id}", response_model=POLineItemReadWithPO)
async def read_orderlineitem(session: Annotated[Session, Depends(get_session)], polineitem_id: int):
    polineitem = session.get(POLineItem, polineitem_id)
    if not polineitem:
        raise HTTPException(status_code=404, detail="Purchase order line item not found")
    return polineitem

@polineitem_router.patch("/{id}", response_model=POLineItemRead)
async def update_polineitem(session: Annotated[Session, Depends(get_session)], producer: Annotated[AIOKafkaProducer, Depends(get_kafka_producer)], polineitem_id: int, POLineItemInfo: POLineItemUpdate):
    try:
        po = session.exec(select(POTable).where(POTable.id==POLineItemInfo.PO_NO)).first()
        if not po:
            raise HTTPException(status_code=404, detail="Purchase order not found")

        db_polineitem = session.get(POLineItem, polineitem_id)
        if not db_polineitem:
            raise HTTPException(status_code=404, detail="Purchase order line item not found.")

#        if db_polineitem.Quantity!=POLineItemInfo.Quantity:
#            inventory = await fetch_product_inventories(db_polineitem.ProductID)
            # if inventory['Quantity']<POLineItemInfo.Quantity:
            #     raise HTTPException(status_code=500, detail="Invalid quantity.")

        polineitem_data = POLineItemInfo.model_dump(exclude_unset=True)
        for key, value in polineitem_data.items():
            setattr(db_polineitem, key, value)
        session.add(db_polineitem)
        session.commit()
        session.refresh(db_polineitem)

        PurchaseOrderLineItemInformation_dict = {field: getattr(db_polineitem, field) for field in db_polineitem.model_dump()}
        PurchaseOrderLineItemInformation_json = json.dumps(PurchaseOrderLineItemInformation_dict).encode("utf-8")
        # Produce message
        await producer.send_and_wait("UpdatePOLineItem", PurchaseOrderLineItemInformation_json)
    except:
        raise HTTPException(status_code=500, detail="Invalid data")
    return db_polineitem

@polineitem_router.put("/{id}", response_model=POLineItemRead)
async def replace_polineitem(session: Annotated[Session, Depends(get_session)], producer: Annotated[AIOKafkaProducer, Depends(get_kafka_producer)], polineitem_id: int, POLineItemInfo: POLineItemUpdateComplete):
    try:
        order = session.exec(select(POTable).where(POTable.id==POLineItemInfo.PO_NO, POTable.EnableEdit==True)).first()
        if not order:
            raise HTTPException(status_code=404, detail="Purchase Order not found")
#        inventory = await fetch_product_inventories(OrderLineItemInfo.ProductID)
#        if inventory['Quantity']<OrderLineItemInfo.Quantity:
#            raise HTTPException(status_code=500, detail="Invalid quantity.")

        db_orderlineitem = session.get(POLineItem, polineitem_id)
        if not db_orderlineitem:
            raise HTTPException(status_code=404, detail="Purchase Order line item not found.")
        orderlineitem_data = POLineItemInfo.model_dump()
        for key, value in orderlineitem_data.items():
            setattr(db_orderlineitem, key, value)
        session.add(db_orderlineitem)
        session.commit()
        session.refresh(db_orderlineitem)

        PurchaseOrderLineItemInformation_dict = {field: getattr(db_orderlineitem, field) for field in db_orderlineitem.model_dump()}
        PurchaseOrderLineItemInformation_json = json.dumps(PurchaseOrderLineItemInformation_dict).encode("utf-8")
        # Produce message
        await producer.send_and_wait("ReplacePOLineItem", PurchaseOrderLineItemInformation_json)
    except:
        raise HTTPException(status_code=500, detail="Invalid data")
    return db_orderlineitem

@polineitem_router.delete("/{id}", response_model=POLineItemRead)
async def delete_polineitem(session: Annotated[Session, Depends(get_session)], producer: Annotated[AIOKafkaProducer, Depends(get_kafka_producer)], orderlineitem_id: int, OrderLineItemInfo: POLineItemUpdateComplete):
    try:
        order = session.exec(select(POTable).where(POTable.id==OrderLineItemInfo.PO_NO, POTable.EnableEdit==True)).first()
        if not order:
            raise HTTPException(status_code=404, detail="Purchase Order not found")

        db_orderlineitem = session.get(POLineItem, orderlineitem_id)
        if not db_orderlineitem:
            raise HTTPException(status_code=404, detail="Purchase Order line item not found.")
        session.delete(db_orderlineitem)
        session.commit()
#        session.refresh(db_orderlineitem)

        PurchaseOrderLineItemInformation_dict = {field: getattr(db_orderlineitem, field) for field in db_orderlineitem.model_dump()}
        PurchaseOrderLineItemInformation_json = json.dumps(PurchaseOrderLineItemInformation_dict).encode("utf-8")
        # Produce message
        await producer.send_and_wait("DeletePOLineItem", PurchaseOrderLineItemInformation_json)
    except:
        raise HTTPException(status_code=500, detail="Invalid data")
    return db_orderlineitem
