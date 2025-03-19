from pymongo import MongoClient
import os

MONGO_URI = os.getenv("MONGODB_URI")
DB_NAME = "valodiscordhub"

client = MongoClient(MONGO_URI)
db = client[DB_NAME]

collections = ["admin_logs", "leaderboards", "matches", "players", "queues"]

for col in collections:
    if col not in db.list_collection_names():
        db.create_collection(col)

print("Database initialized successfully.")
