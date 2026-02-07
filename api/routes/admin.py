from fastapi import APIRouter, Depends, HTTPException, Query, Body
from db import get_db
from auth import require_bot_token
from models.admin_log import AdminLog
from models.updates import AdminLogCreate
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List, Optional
from datetime import datetime, timezone

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/logs", response_model=List[AdminLog])
async def list_admin_logs(
    action: Optional[str] = Query(None, description="Filter by action type"),
    admin_discord_id: Optional[str] = Query(
        None, description="Filter by admin who performed the action"
    ),
    target_discord_id: Optional[str] = Query(
        None, description="Filter by target player"
    ),
    match_id: Optional[str] = Query(None, description="Filter by match ID"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(
        50, ge=1, le=100, description="Maximum number of records to return"
    ),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    List admin logs with filtering and pagination.

    Returns admin action logs sorted by timestamp (newest first).
    """
    query = {}
    if action:
        query["action"] = action
    if admin_discord_id:
        query["admin_discord_id"] = admin_discord_id
    if target_discord_id:
        query["target_discord_id"] = target_discord_id
    if match_id:
        query["match_id"] = match_id

    cursor = db.admin_logs.find(query).sort("timestamp", -1).skip(skip).limit(limit)
    return [AdminLog(**doc) async for doc in cursor]


@router.get("/logs/count")
async def count_admin_logs(
    action: Optional[str] = Query(None, description="Filter by action type"),
    admin_discord_id: Optional[str] = Query(None, description="Filter by admin"),
    target_discord_id: Optional[str] = Query(None, description="Filter by target"),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Get count of admin logs for pagination."""
    query = {}
    if action:
        query["action"] = action
    if admin_discord_id:
        query["admin_discord_id"] = admin_discord_id
    if target_discord_id:
        query["target_discord_id"] = target_discord_id

    count = await db.admin_logs.count_documents(query)
    return {"count": count}


@router.get("/bans", response_model=List[dict])
async def get_banned_players(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(
        50, ge=1, le=100, description="Maximum number of records to return"
    ),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Get list of banned players with pagination.

    Returns ban records sorted by timestamp (newest first).
    """
    cursor = (
        db.admin_logs.find(
            {"action": "ban", "target_discord_id": {"$exists": True}},
            {
                "target_discord_id": 1,
                "reason": 1,
                "timestamp": 1,
                "admin_discord_id": 1,
            },
        )
        .sort("timestamp", -1)
        .skip(skip)
        .limit(limit)
    )
    return [doc async for doc in cursor]


@router.get("/bans/count")
async def count_banned_players(db: AsyncIOMotorDatabase = Depends(get_db)):
    """Get total count of banned players."""
    count = await db.admin_logs.count_documents(
        {"action": "ban", "target_discord_id": {"$exists": True}}
    )
    return {"count": count}


@router.get("/timeouts", response_model=List[dict])
async def get_timeout_players(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(
        50, ge=1, le=100, description="Maximum number of records to return"
    ),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Get list of timed-out players with pagination.

    Returns timeout records sorted by timestamp (newest first).
    """
    cursor = (
        db.admin_logs.find(
            {"action": "timeout", "target_discord_id": {"$exists": True}},
            {
                "target_discord_id": 1,
                "reason": 1,
                "duration_minutes": 1,
                "timestamp": 1,
                "admin_discord_id": 1,
            },
        )
        .sort("timestamp", -1)
        .skip(skip)
        .limit(limit)
    )
    return [doc async for doc in cursor]


@router.get("/timeouts/count")
async def count_timeout_players(db: AsyncIOMotorDatabase = Depends(get_db)):
    """Get total count of timed-out players."""
    count = await db.admin_logs.count_documents(
        {"action": "timeout", "target_discord_id": {"$exists": True}}
    )
    return {"count": count}


@router.get("/check-ban/{discord_id}", response_model=bool)
async def is_player_banned(discord_id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    """Check if a player is currently banned."""
    doc = await db.admin_logs.find_one(
        {"action": "ban", "target_discord_id": discord_id}
    )
    return bool(doc)


@router.get("/check-timeout/{discord_id}", response_model=bool)
async def is_player_timeout(
    discord_id: str, db: AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Check if a player is currently in timeout.

    Automatically removes expired timeouts from the database.
    """
    timeout = await db.admin_logs.find_one(
        {"action": "timeout", "target_discord_id": discord_id}
    )
    if not timeout:
        return False

    timeout_time = timeout["timestamp"]
    if timeout_time.tzinfo is None:
        timeout_time = timeout_time.replace(tzinfo=timezone.utc)
    duration = timeout["duration_minutes"]
    current_time = datetime.now(timezone.utc)

    time_diff = (current_time - timeout_time).total_seconds() / 60.0

    if time_diff >= duration:
        # Timeout has expired, remove it
        await db.admin_logs.delete_one(
            {"action": "timeout", "target_discord_id": discord_id}
        )
        return False

    return True


@router.get("/check-timeout/{discord_id}/remaining")
async def get_timeout_remaining(
    discord_id: str, db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Get remaining timeout duration for a player in minutes."""
    timeout = await db.admin_logs.find_one(
        {"action": "timeout", "target_discord_id": discord_id}
    )
    if not timeout:
        return {"is_timeout": False, "remaining_minutes": 0}

    timeout_time = timeout["timestamp"]
    if timeout_time.tzinfo is None:
        timeout_time = timeout_time.replace(tzinfo=timezone.utc)
    duration = timeout["duration_minutes"]
    current_time = datetime.now(timezone.utc)

    time_diff = (current_time - timeout_time).total_seconds() / 60.0
    remaining = duration - time_diff

    if remaining <= 0:
        await db.admin_logs.delete_one(
            {"action": "timeout", "target_discord_id": discord_id}
        )
        return {"is_timeout": False, "remaining_minutes": 0}

    return {
        "is_timeout": True,
        "remaining_minutes": round(remaining, 1),
        "reason": timeout.get("reason"),
    }


@router.delete(
    "/logs/{action}/{target_discord_id}", dependencies=[Depends(require_bot_token)]
)
async def remove_admin_log(
    action: str, target_discord_id: str, db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Remove an admin log entry. Bot only."""
    result = await db.admin_logs.delete_one(
        {"action": action, "target_discord_id": target_discord_id}
    )
    if result.deleted_count == 0:
        raise HTTPException(
            status_code=404,
            detail=f"Admin log for action '{action}' and target '{target_discord_id}' was not found.",
        )
    return {"message": "Admin log removed successfully"}


@router.post("/ban", response_model=AdminLog, dependencies=[Depends(require_bot_token)])
async def ban_player(
    log: AdminLogCreate = Body(...), db: AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Ban a player. Bot only.

    Creates a ban record that will prevent the player from joining queues.
    """
    if not log.target_discord_id:
        raise HTTPException(
            status_code=400, detail="target_discord_id is required to ban a player"
        )

    # Check if already banned
    existing = await db.admin_logs.find_one(
        {"action": "ban", "target_discord_id": log.target_discord_id}
    )
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Player '{log.target_discord_id}' is already banned",
        )

    log_dict = log.model_dump()
    log_dict["timestamp"] = datetime.now(timezone.utc)
    log_dict["action"] = "ban"
    await db.admin_logs.insert_one(log_dict)
    return AdminLog(**log_dict)


@router.post(
    "/timeout", response_model=AdminLog, dependencies=[Depends(require_bot_token)]
)
async def timeout_player(
    log: AdminLogCreate = Body(...), db: AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Timeout a player. Bot only.

    Creates a timeout record that will temporarily prevent the player from joining queues.
    The timeout expires after the specified duration_minutes.
    """
    if not log.target_discord_id:
        raise HTTPException(
            status_code=400, detail="target_discord_id is required to timeout a player"
        )
    if not log.duration_minutes:
        raise HTTPException(
            status_code=400,
            detail="duration_minutes is required for timeout (how long the timeout should last)",
        )

    # Remove existing timeout if any
    await db.admin_logs.delete_one(
        {"action": "timeout", "target_discord_id": log.target_discord_id}
    )

    log_dict = log.model_dump()
    log_dict["timestamp"] = datetime.now(timezone.utc)
    log_dict["action"] = "timeout"
    await db.admin_logs.insert_one(log_dict)
    return AdminLog(**log_dict)


@router.post(
    "/unban", response_model=AdminLog, dependencies=[Depends(require_bot_token)]
)
async def unban_player(
    log: AdminLogCreate = Body(...), db: AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Unban a player. Bot only.

    Removes the ban record and creates an unban log entry.
    """
    if not log.target_discord_id:
        raise HTTPException(
            status_code=400, detail="target_discord_id is required to unban a player"
        )

    # Remove the ban
    result = await db.admin_logs.delete_one(
        {"action": "ban", "target_discord_id": log.target_discord_id}
    )
    if result.deleted_count == 0:
        raise HTTPException(
            status_code=404,
            detail=f"Player '{log.target_discord_id}' is not currently banned",
        )

    # Create unban log entry
    log_dict = log.model_dump()
    log_dict["timestamp"] = datetime.now(timezone.utc)
    log_dict["action"] = "unban"
    await db.admin_logs.insert_one(log_dict)
    return AdminLog(**log_dict)
