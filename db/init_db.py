from pymongo import MongoClient, ASCENDING, DESCENDING
import os
import time

MONGO_URI = os.getenv("MONGODB_URI")

def wait_for_mongodb(max_retries=5, retry_delay=5):
    for attempt in range(max_retries):
        try:
            client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
            client.server_info()
            return client
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"Attempt {attempt + 1}/{max_retries}: MongoDB connection failed: {str(e)}")
                print(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                raise Exception(f"Could not connect to MongoDB after maximum retries: {str(e)}")

def create_indexes(db):
    db.players.create_index([("discord_id", ASCENDING)], unique=True)
    db.players.create_index([("riot_id", ASCENDING)], unique=True)
    db.players.create_index([("rank", ASCENDING)])
    db.players.create_index([("points", DESCENDING)])
    
    db.matches.create_index([("match_id", ASCENDING)], unique=True)
    db.matches.create_index([("created_at", DESCENDING)])
    db.matches.create_index([("result", ASCENDING)])
    db.matches.create_index([("players_red", ASCENDING)])
    db.matches.create_index([("players_blue", ASCENDING)])

    db.leaderboards.create_index([("rank_group", ASCENDING), ("players.discord_id", ASCENDING)], unique=True)
    db.leaderboards.create_index([("last_updated", DESCENDING)])

    db.queues.create_index([("rank_group", ASCENDING)], unique=True)
    db.queues.create_index([("players.discord_id", ASCENDING)])

    db.admin_logs.create_index([("timestamp", DESCENDING)])
    db.admin_logs.create_index([("action", ASCENDING)])
    db.admin_logs.create_index([("admin_discord_id", ASCENDING)])
    db.admin_logs.create_index([("target_discord_id", ASCENDING)])

try:
    print(f"Attempting to connect to MongoDB with URI: {MONGO_URI}")
    client = wait_for_mongodb()
    db = client.valodiscordhub

    collections = ["admin_logs", "leaderboards", "matches", "players", "queues"]

    for col in collections:
        if col not in db.list_collection_names():
            db.create_collection(col)
            print(f"Created collection: {col}")

    create_indexes(db)
    print("Database indexes created successfully.")
    print("Database initialized successfully.")
except Exception as e:
    print(f"Error initializing database: {e}")
    exit(1)
