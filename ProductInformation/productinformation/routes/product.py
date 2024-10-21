import json
from typing import Annotated
from sqlmodel import Session, select
from app.db import get_session
from productinformation.model.database import ProductInformation
from fastapi import APIRouter, HTTPException, Query, Depends
from productinformation.schemas.schemas import ProductCreate, ProductRead, ProductUpdate, ProductUpdateComplete, ProductReadWithCatagory
from aiokafka import AIOKafkaProducer # type: ignore
from datetime import datetime

product_router = APIRouter(prefix="/products", tags=["product"])

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

@product_router.post("/", response_model=ProductRead)
async def create_product(ProductInfo: ProductCreate, session: Annotated[Session, Depends(get_session)], producer2: Annotated[AIOKafkaProducer, Depends(get_kafka_producer)]):
    try:
        # Produce message
        ProductInformation_dict = {field: getattr(ProductInfo, field) for field in ProductInfo.model_dump()}
        ProductInformation_json = json.dumps(ProductInformation_dict, default=json_serializer).encode("utf-8")
        await producer2.send_and_wait("CreateProduct", ProductInformation_json)

        db_product = ProductInformation.model_validate(ProductInfo)
        session.add(db_product)
        session.commit()
        session.refresh(db_product)
    except:
        raise HTTPException(status_code=500, detail="Invalid Data")
    return db_product

@product_router.get("/", response_model=list[ProductReadWithCatagory])
async def read_products(session: Annotated[Session, Depends(get_session)], offset: int = 0, limit: int = Query(default=100, le=100)):
    products = session.exec(select(ProductInformation).where(ProductInformation.Enabled == True).offset(offset).limit(limit)).all()
    return products

@product_router.get("/{id}", response_model=ProductReadWithCatagory)
async def read_product(session: Annotated[Session, Depends(get_session)], id: int):
    product = session.exec(select(ProductInformation).where(ProductInformation.id == id, ProductInformation.Enabled == True)).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

@product_router.patch("/{product_id}", response_model=ProductRead)
async def update_product(session: Annotated[Session, Depends(get_session)], producer2: Annotated[AIOKafkaProducer, Depends(get_kafka_producer)], product_id: int, ProductInfo: ProductUpdate):
    try:
        db_product = session.get(ProductInformation, product_id)
        if not db_product:
            raise HTTPException(status_code=404, detail="Product not found.")
        product_data = ProductInfo.model_dump(exclude_unset=True)
        for key, value in product_data.items():
            setattr(db_product, key, value)
        session.add(db_product)
        session.commit()
        session.refresh(db_product)

        ProductInformation_dict = {field: getattr(db_product, field) for field in db_product.model_dump()}
        ProductInformation_json = json.dumps(ProductInformation_dict, default=json_serializer).encode("utf-8")
        # Produce message
        await producer2.send_and_wait("UpdateProduct", ProductInformation_json)
    except:
        raise HTTPException(status_code=500, detail="Invalid Data")
    return db_product

@product_router.put("/{product_id}", response_model=ProductRead)
async def replace_product(session: Annotated[Session, Depends(get_session)], producer2: Annotated[AIOKafkaProducer, Depends(get_kafka_producer)], product_id: int, ProductInfo: ProductUpdateComplete):
    try:
        db_product = session.get(ProductInformation, product_id)
        if not db_product:
            raise HTTPException(status_code=404, detail="Product not found.")
        product_data = ProductInfo.model_dump()
        for key, value in product_data.items():
            setattr(db_product, key, value)
        session.add(db_product)
        session.commit()
        session.refresh(db_product)

        ProductInformation_dict = {field: getattr(db_product, field) for field in db_product.model_dump()}
        ProductInformation_json = json.dumps(ProductInformation_dict, default=json_serializer).encode("utf-8")
        # Produce message
        await producer2.send_and_wait("ReplaceProduct", ProductInformation_json)
    except:
        raise HTTPException(status_code=500, detail="Invalid Data")
    return db_product

@product_router.delete("/{product_id}", response_model=ProductRead)
async def delete_product(session: Annotated[Session, Depends(get_session)], producer2: Annotated[AIOKafkaProducer, Depends(get_kafka_producer)], product_id: int):
    try:
        db_product = session.get(ProductInformation, product_id)
        if not db_product:
            raise HTTPException(status_code=404, detail="Product not found.")
        key = "Enabled"
        value = False
        setattr(db_product, key, value)
        session.add(db_product)
        session.commit()
        session.refresh(db_product)

        ProductInformation_dict = {field: getattr(db_product, field) for field in db_product.model_dump()}
        ProductInformation_json = json.dumps(ProductInformation_dict, default=json_serializer).encode("utf-8")
        # Produce message
        await producer2.send_and_wait("DeleteProduct", ProductInformation_json)
    except:
        raise HTTPException(status_code=500, detail="Invalid Data")
    return db_product
