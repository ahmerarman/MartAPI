# main.py
from contextlib import asynccontextmanager
from typing import Union, Optional, Annotated

import requests # type: ignore
from app import settings
from sqlmodel import Field, Session, SQLModel, create_engine, select
from fastapi import FastAPI, Depends
from typing import AsyncGenerator
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer # type: ignore
import asyncio
import json

class Todo(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    content: str = Field(index=True)


async def run_microservice02():
    api_url = f"http://api2:8000/"
    headers = {
        "Content-Type": "application/json"
    }
    response = requests.get(api_url, headers=headers)
    response.raise_for_status()


# only needed for psycopg 3 - replace postgresql
# with postgresql+psycopg in settings.DATABASE_URL
connection_string = str(settings.DATABASE_URL).replace(
    "postgresql", "postgresql+psycopg"
)


# recycle connections after 5 minutes
# to correspond with the compute scale down
engine = create_engine(
    connection_string, connect_args={}, pool_recycle=300
)


def create_db_and_tables()->None:
    SQLModel.metadata.create_all(engine)

async def consume_messages(topic, bootstrap_servers):
    # Create a consumer instance.
    consumer = AIOKafkaConsumer(
        topic,
        bootstrap_servers=bootstrap_servers,
        group_id="my-group",
        auto_offset_reset='earliest'
    )

    # Start the consumer.
    await consumer.start()
    try:
        # Continuously listen for messages.
        async for message in consumer:
            print(f"TODO Received message: {message.value.decode()} on topic {message.topic}")
            # Here you can add code to process each message.
#            await run_microservice02()
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
    print("Creating tables..")
    # loop.run_until_complete(consume_messages('todos', 'broker:19092'))

    task = asyncio.create_task(consume_messages('todos', 'broker:19092'))
    
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

def get_session():
    with Session(engine) as session:
        yield session


@app.get("/")
def read_root():
    return {"Hello": "Ahmer Arman"}

# Kafka Producer as a dependency
async def get_kafka_producer():
    producer = AIOKafkaProducer(bootstrap_servers='broker:19092')
    await producer.start()
    try:
        yield producer
    finally:
        await producer.stop()

@app.post("/todos/", response_model=Todo)
async def create_todo(todo: Todo, session: Annotated[Session, Depends(get_session)], producer: Annotated[AIOKafkaProducer, Depends(get_kafka_producer)])->Todo:
        todo_dict = {field: getattr(todo, field) for field in todo.model_dump()}
        todo_json = json.dumps(todo_dict).encode("utf-8")
#        print("todoJSON:", todo_json)
        # Produce message
        await producer.send_and_wait("todos", todo_json)
        session.add(todo)
        session.commit()
        session.refresh(todo)
        return todo


@app.get("/todos/", response_model=list[Todo])
def read_todos(session: Annotated[Session, Depends(get_session)]):
        todos = session.exec(select(Todo)).all()
        return todos
