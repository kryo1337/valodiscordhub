import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGODB_URI")
MONGO_DB = os.getenv("MONGODB_DB")

client = AsyncIOMotorClient(MONGO_URI)
db = client[MONGO_DB]

def get_db():
    return db
