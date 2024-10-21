# main.py
from contextlib import asynccontextmanager

import requests # type: ignore
from app.db import create_db_and_tables
from inventory.routes.inventory import inventory_router

from fastapi import FastAPI, HTTPException
from typing import AsyncGenerator
from aiokafka import AIOKafkaConsumer # type: ignore
import asyncio

async def run_microservice():
    api_url = f"http://api2:8000/"
    headers = {
        "Content-Type": "application/json"
    }
    try:
        response = requests.get(api_url, headers=headers)
        response.raise_for_status()
        return response.json
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=response.status_code, detail=str(response.json))


async def consume_messages(topic, bootstrap_servers):
    # Create a consumer instance.
    consumer = AIOKafkaConsumer(
        topic,
        bootstrap_servers=bootstrap_servers,
        group_id="inventory-group",
        auto_offset_reset='earliest'
    )

    # Start the consumer.
    await consumer.start()
    try:
        # Continuously listen for messages.
        async for message in consumer:
            print(f"Inventory Information received message: {message.value.decode()} on topic {message.topic}")
            # Here you can add code to process each message.
            # Example: parse the message, store it in a database, etc.
#            microservice = run_microservice()
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

    task1 = asyncio.create_task(consume_messages('Inventory', 'broker:19092'))
    
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
app.include_router(inventory_router)
#app.include_router(catagory_router)


@app.get("/")
def read_root():
    return {"Hello": "Ahmer Arman"}
