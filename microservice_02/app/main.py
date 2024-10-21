# main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from typing import AsyncGenerator
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer # type: ignore
import asyncio

import json

async def consume_messages(topic, bootstrap_servers):
    # Create a consumer instance.
    consumer = AIOKafkaConsumer(
        topic,
        bootstrap_servers=bootstrap_servers,
        group_id="microservices-group",
        auto_offset_reset='earliest'
    )
    # Start the consumer.
    await consumer.start()
    try:
        # Continuously listen for messages.
        async for message in consumer:
            print(f"Microservice2 Received message: {message.value.decode()} on topic {message.topic}")
            # Here you can add code to process each message.
            # Example: parse the message, store it in a database, etc.
    finally:
        # Ensure to close the consumer when done.
        await consumer.stop()


# The first part of the function, before the yield, will
# be executed before the application starts.
# https://fastapi.tiangolo.com/advanced/events/#lifespan-function
# loop = asyncio.get_event_loop()
@asynccontextmanager
async def lifespan(app: FastAPI)-> AsyncGenerator[None, None]:
    # loop.run_until_complete(consume_messages('todos', 'broker:19092'))
    # print("Creating tables..")

#    task1 = asyncio.create_task(consume_messages('todos', 'broker:19092'))
#    task2 = asyncio.create_task(consume_messages('CreateVendor', 'broker:19092'))
#    task3 = asyncio.create_task(consume_messages('UpdateVendor', 'broker:19092'))
#    task4 = asyncio.create_task(consume_messages('ReplaceVendor', 'broker:19092'))
#    task5 = asyncio.create_task(consume_messages('DeleteVendor', 'broker:19092'))
#    task6 = asyncio.create_task(consume_messages('CreateProduct', 'broker:19092'))
#    task7 = asyncio.create_task(consume_messages('UpdateProduct', 'broker:19092'))
#    task8 = asyncio.create_task(consume_messages('ReplaceProduct', 'broker:19092'))
#    task9 = asyncio.create_task(consume_messages('DeleteProduct', 'broker:19092'))
#    task10 = asyncio.create_task(consume_messages('Catagory', 'broker:19092'))
#    task11 = asyncio.create_task(consume_messages('Inventory', 'broker:19092'))
#    yield

    tasks = [
        asyncio.create_task(consume_messages('todos', 'broker:19092')),
        asyncio.create_task(consume_messages('CreateVendor', 'broker:19092')),
        asyncio.create_task(consume_messages('UpdateVendor', 'broker:19092')),
        asyncio.create_task(consume_messages('ReplaceVendor', 'broker:19092')),
        asyncio.create_task(consume_messages('DeleteVendor', 'broker:19092')),
        asyncio.create_task(consume_messages('CreateProduct', 'broker:19092')),
        asyncio.create_task(consume_messages('UpdateProduct', 'broker:19092')),
        asyncio.create_task(consume_messages('ReplaceProduct', 'broker:19092')),
        asyncio.create_task(consume_messages('DeleteProduct', 'broker:19092')),
        asyncio.create_task(consume_messages('Catagory', 'broker:19092')),
        asyncio.create_task(consume_messages('Inventory', 'broker:19092')),
        asyncio.create_task(consume_messages('CreateOrder', 'broker:19092')),
        asyncio.create_task(consume_messages('UpdateOrder', 'broker:19092')),
        asyncio.create_task(consume_messages('ReplaceOrder', 'broker:19092')),
        asyncio.create_task(consume_messages('DeleteOrder', 'broker:19092')),
        asyncio.create_task(consume_messages('CreateOrderLineItem', 'broker:19092')),
        asyncio.create_task(consume_messages('UpdateOrderLineItem', 'broker:19092')),
        asyncio.create_task(consume_messages('ReplaceOrderLineItem', 'broker:19092')),
        asyncio.create_task(consume_messages('DeleteOrderLineItem', 'broker:19092'))
    ]
    yield
#    for task in tasks:
#        task.cancel()
#    await asyncio.gather(*tasks, return_exceptions=True)


app = FastAPI(lifespan=lifespan, title="Hello World API with DB", 
    version="0.0.1",
#    servers=[
#        {
#            "url": "http://127.0.0.1:8002", # ADD NGROK URL Here Before Creating GPT Action
#            "description": "Development Server"
#        },{
#            "url": "http://127.0.0.1:8000", # ADD NGROK URL Here Before Creating GPT Action
#            "description": "Development Server"
#        }
#        ]
)


@app.get("/")
def read_root():
    return {"App": "Service 2"}

# Kafka Producer as a dependency
async def get_kafka_producer():
    producer = AIOKafkaProducer(bootstrap_servers='broker:19092')
    await producer.start()
    try:
        yield producer
    finally:
        await producer.stop()
