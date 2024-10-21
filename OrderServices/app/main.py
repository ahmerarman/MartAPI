# main.py
from contextlib import asynccontextmanager

import requests # type: ignore
from orderservices.model.database import OrderTable
from app.db import create_db_and_tables
from orderservices.routes.order import order_router
from orderservices.routes.orderlineitem import orderlineitem_router

from fastapi import FastAPI, HTTPException
from typing import AsyncGenerator
from aiokafka import AIOKafkaConsumer # type: ignore
import asyncio


async def run_microservice02():
    api_url = f"http://api2:8000/"
    headers = {
        "Content-Type": "application/json"
    }
    response = requests.get(api_url, headers=headers)
    response.raise_for_status()

## Implementation will be changed for following method
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

## Implementation will be changed for following method
async def fetch_product_inventories(order: OrderTable):
    api_url = f"http://api5:8000/inventory/"
    headers = {
        "Content-Type": "application/json"
    }
    try:
        response = requests.get(api_url, headers=headers)
        response.raise_for_status()
        records = response.json()
        for record in records:
            if order.id == record['ProductID']:
                await patch_inventory_status(record['id'], order.EnableEdit)
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=response.status_code, detail=str(response.json))


async def consume_messages(topic, bootstrap_servers):
    # Create a consumer instance.
    consumer = AIOKafkaConsumer(
        topic,
        bootstrap_servers=bootstrap_servers,
        group_id="orderservices-group",
        auto_offset_reset='earliest'
    )
    # Start the consumer.
    await consumer.start()
    try:
        # Continuously listen for messages.
        async for message in consumer:
            print(f"Order Information received message: {message.value.decode()} on topic {message.topic}")
            # Here you can add code to process each message.
            # Example: parse the message, store it in a database, etc.
#            await run_microservice02()
#            if message.topic in ["DeleteProduct", "UpdateProduct", "ReplaceProduct"]:
#                message_dict = json.loads(message.value.decode())
#                order_info = OrderTable.model_validate(message_dict)
#                await fetch_product_inventories(order_info)
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

    task1 = asyncio.create_task(consume_messages('CreateOrder', 'broker:19092'))
    task2 = asyncio.create_task(consume_messages('UpdateOrder', 'broker:19092'))
    task3 = asyncio.create_task(consume_messages('ReplaceOrder', 'broker:19092'))
    task4 = asyncio.create_task(consume_messages('DeleteOrder', 'broker:19092'))
    task5 = asyncio.create_task(consume_messages('CreateOrderLineItem', 'broker:19092'))
    task6 = asyncio.create_task(consume_messages('UpdateOrderLineItem', 'broker:19092'))
    task7 = asyncio.create_task(consume_messages('ReplaceOrderLineItem', 'broker:19092'))
    task8 = asyncio.create_task(consume_messages('DeleteOrderLineItem', 'broker:19092'))
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
app.include_router(order_router)
app.include_router(orderlineitem_router)


@app.get("/")
def read_root():
    return {"Hello": "Ahmer Arman"}

# Kafka Producer as a dependency
#async def get_kafka_producer():
#    producer = AIOKafkaProducer(bootstrap_servers='broker:19092')
#    await producer.start()
#    try:
#        yield producer
#    finally:
#        await producer.stop()
