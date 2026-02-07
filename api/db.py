"""
Database connection module with optimized connection pooling.
Uses Motor (async MongoDB driver) with configurable pool settings.
"""

import logging
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING
from typing import Optional
from config import settings

logger = logging.getLogger("valohub")

# Global client and database references
_client: Optional[AsyncIOMotorClient] = None
_db: Optional[AsyncIOMotorDatabase] = None


def get_client() -> AsyncIOMotorClient:
    """Get or create the MongoDB client with optimized connection pooling."""
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(
            settings.mongodb_uri,
            maxPoolSize=settings.mongo_max_pool_size,
            minPoolSize=settings.mongo_min_pool_size,
            maxIdleTimeMS=settings.mongo_max_idle_time_ms,
            serverSelectionTimeoutMS=settings.mongo_server_selection_timeout_ms,
            # Additional recommended settings
            retryWrites=True,
            retryReads=True,
            w="majority",  # Write concern for durability
        )
        logger.info(
            f"MongoDB client created with pool size {settings.mongo_min_pool_size}-{settings.mongo_max_pool_size}"
        )
    return _client


def get_db() -> AsyncIOMotorDatabase:
    """Get the database instance."""
    global _db
    if _db is None:
        client = get_client()
        _db = client[settings.mongodb_db]
        logger.info(f"Connected to database: {settings.mongodb_db}")
    return _db


async def init_indexes() -> None:
    """
    Create database indexes for optimal query performance.
    Should be called on application startup.
    """
    db = get_db()

    # Players collection indexes
    await db.players.create_index("discord_id", unique=True, background=True)
    await db.players.create_index("riot_id", background=True)
    await db.players.create_index("points", background=True)
    logger.info("Created indexes for players collection")

    # Matches collection indexes
    await db.matches.create_index("match_id", unique=True, background=True)
    await db.matches.create_index("result", background=True)  # For active matches query
    await db.matches.create_index("rank_group", background=True)
    await db.matches.create_index("created_at", background=True)
    await db.matches.create_index(
        [("players_red", ASCENDING), ("players_blue", ASCENDING)], background=True
    )
    logger.info("Created indexes for matches collection")

    # Admin logs collection indexes
    await db.admin_logs.create_index(
        [("action", ASCENDING), ("target_discord_id", ASCENDING)], background=True
    )
    await db.admin_logs.create_index("timestamp", background=True)
    await db.admin_logs.create_index("admin_discord_id", background=True)
    logger.info("Created indexes for admin_logs collection")

    # Leaderboards collection indexes
    await db.leaderboards.create_index("rank_group", unique=True, background=True)
    logger.info("Created indexes for leaderboards collection")

    # Queues collection indexes
    await db.queues.create_index("rank_group", unique=True, background=True)
    logger.info("Created indexes for queues collection")

    # Preferences collection indexes
    await db.preferences.create_index("discord_id", unique=True, background=True)
    logger.info("Created indexes for preferences collection")

    logger.info("All database indexes created successfully")


async def close_db() -> None:
    """Close the database connection. Should be called on application shutdown."""
    global _client, _db
    if _client is not None:
        _client.close()
        _client = None
        _db = None
        logger.info("MongoDB connection closed")


async def check_connection() -> bool:
    """Check if the database connection is healthy."""
    try:
        db = get_db()
        await db.command("ping")
        return True
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return False
