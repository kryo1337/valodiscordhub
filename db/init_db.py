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
                print(
                    f"Attempt {attempt + 1}/{max_retries}: MongoDB connection failed: {str(e)}"
                )
                print(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                raise Exception(
                    f"Could not connect to MongoDB after maximum retries: {str(e)}"
                )


def create_indexes(db):
    db.players.create_index([("discord_id", ASCENDING)], unique=True, background=True)
    db.players.create_index([("riot_id", ASCENDING)], background=True)
    db.players.create_index([("points", ASCENDING)], background=True)

    db.matches.create_index([("match_id", ASCENDING)], unique=True, background=True)
    db.matches.create_index([("result", ASCENDING)], background=True)
    db.matches.create_index([("rank_group", ASCENDING)], background=True)
    db.matches.create_index([("created_at", ASCENDING)], background=True)
    db.matches.create_index(
        [("players_red", ASCENDING), ("players_blue", ASCENDING)], background=True
    )

    db.admin_logs.create_index(
        [("action", ASCENDING), ("target_discord_id", ASCENDING)], background=True
    )
    db.admin_logs.create_index([("timestamp", ASCENDING)], background=True)
    db.admin_logs.create_index([("admin_discord_id", ASCENDING)], background=True)

    db.leaderboards.create_index(
        [("rank_group", ASCENDING)], unique=True, background=True
    )

    db.queues.create_index([("rank_group", ASCENDING)], unique=True, background=True)

    db.preferences.create_index(
        [("discord_id", ASCENDING)], unique=True, background=True
    )


try:
    print(f"Attempting to connect to MongoDB with URI: {MONGO_URI}")
    client = wait_for_mongodb()
    db = client.valodiscordhub

    collections = [
        "admin_logs",
        "leaderboards",
        "matches",
        "players",
        "queues",
        "preferences",
    ]

    for col in collections:
        if col not in db.list_collection_names():
            db.create_collection(col)
            print(f"Created collection: {col}")

    create_indexes(db)
    print("Database indexes created successfully.")

    # Initialize queues
    rank_groups = ["iron-plat", "dia-asc", "imm-radiant"]
    for group in rank_groups:
        db.queues.update_one(
            {"rank_group": group},
            {"$setOnInsert": {"rank_group": group, "players": []}},
            upsert=True,
        )
        print(f"Initialized queue for {group}")

    # Initialize leaderboards
    for group in rank_groups:
        db.leaderboards.update_one(
            {"rank_group": group},
            {
                "$setOnInsert": {
                    "rank_group": group,
                    "players": [],
                    "last_updated": time.time(),
                }
            },
            upsert=True,
        )
        print(f"Initialized leaderboard for {group}")

    print("Database initialized successfully.")
except Exception as e:
    print(f"Error initializing database: {e}")
    exit(1)
