# main.py
from contextlib import asynccontextmanager

import requests # type: ignore
from poservices.model.database import POTable
from app.db import create_db_and_tables
from poservices.routes.PurchaseOrder import po_router
from poservices.routes.PurchaseOrderlineitem import polineitem_router
#from poservices.routes.orderlineitem import orderlineitem_router

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
#async def patch_inventory_status(record_id: int):
#    api_url = f"http://api5:8000/inventory/{record_id}"
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

## Implementation will be changed for following method
#async def fetch_product_inventories(po: POTable):
#    api_url = f"http://api5:8000/inventory/"
#    headers = {
#        "Content-Type": "application/json"
#    }
#    try:
#        response = requests.get(api_url, headers=headers)
#        response.raise_for_status()
#        records = response.json()
#        for record in records:
#            if po.id == record['ProductID']:
#                await patch_inventory_status(record['id'])
#    except requests.exceptions.RequestException as e:
#        raise HTTPException(status_code=response.status_code, detail=str(response.json))


async def consume_messages(topic, bootstrap_servers):
    # Create a consumer instance.
    consumer = AIOKafkaConsumer(
        topic,
        bootstrap_servers=bootstrap_servers,
        group_id="poservices-group",
        auto_offset_reset='earliest'
    )
    # Start the consumer.
    await consumer.start()
    try:
        # Continuously listen for messages.
        async for message in consumer:
            print(f"PO Information received message: {message.value.decode()} on topic {message.topic}")
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

    task1 = asyncio.create_task(consume_messages('CreatePO', 'broker:19092'))
    task2 = asyncio.create_task(consume_messages('UpdatePO', 'broker:19092'))
    task3 = asyncio.create_task(consume_messages('ReplacePO', 'broker:19092'))
    task4 = asyncio.create_task(consume_messages('DeletePO', 'broker:19092'))
    task5 = asyncio.create_task(consume_messages('CreatePOLineItem', 'broker:19092'))
    task6 = asyncio.create_task(consume_messages('UpdatePOLineItem', 'broker:19092'))
    task7 = asyncio.create_task(consume_messages('ReplacePOLineItem', 'broker:19092'))
    task8 = asyncio.create_task(consume_messages('DeletePOLineItem', 'broker:19092'))
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
app.include_router(po_router)
app.include_router(polineitem_router)


@app.get("/")
def read_root():
    return {"Hello": "Ahmer Arman"}
