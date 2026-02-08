from fastapi import APIRouter, Depends, HTTPException, Query, Body, Request
from pydantic import BaseModel
from db import get_db
from auth import require_bot_token, get_request_origin
from models.admin_log import AdminLog
from models.updates import AdminLogCreate
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List, Optional, Dict
from datetime import datetime, timezone
from rate_limit import check_rate_limit


class BatchCheckRequest(BaseModel):
    discord_ids: List[str]


class BatchCheckResponse(BaseModel):
    bans: Dict[str, bool]
    timeouts: Dict[str, bool]


router = APIRouter(prefix="/admin", tags=["admin"])


async def require_admin_rate_limit(request: Request):
    """Rate limit for admin endpoints: 30 requests per minute."""
    origin = get_request_origin(request) or "unknown"
    allowed, count = await check_rate_limit(key=f"admin:{origin}", limit=30, period=60)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail="Too many admin requests. Please try again later.",
            headers={"X-RateLimit-Remaining": str(max(0, 30 - count))},
        )


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

    Checks only the latest timeout log.
    """
    # Find latest timeout
    timeout = await db.admin_logs.find_one(
        {"action": "timeout", "target_discord_id": discord_id}, sort=[("timestamp", -1)]
    )

    if not timeout:
        return False

    timeout_time = timeout["timestamp"]
    if timeout_time.tzinfo is None:
        timeout_time = timeout_time.replace(tzinfo=timezone.utc)
    duration = timeout["duration_minutes"]
    current_time = datetime.now(timezone.utc)

    time_diff = (current_time - timeout_time).total_seconds() / 60.0

    # Return True if active (time_diff < duration)
    return time_diff < duration


@router.get("/check-timeout/{discord_id}/remaining")
async def get_timeout_remaining(
    discord_id: str, db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Get remaining timeout duration for a player in minutes."""
    # Find latest timeout
    timeout = await db.admin_logs.find_one(
        {"action": "timeout", "target_discord_id": discord_id}, sort=[("timestamp", -1)]
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
        return {"is_timeout": False, "remaining_minutes": 0}

    return {
        "is_timeout": True,
        "remaining_minutes": round(remaining, 1),
        "reason": timeout.get("reason"),
    }


@router.delete(
    "/logs/{action}/{target_discord_id}",
    dependencies=[Depends(require_bot_token), Depends(require_admin_rate_limit)],
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


@router.post(
    "/ban",
    response_model=AdminLog,
    dependencies=[Depends(require_bot_token), Depends(require_admin_rate_limit)],
)
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
    "/timeout",
    response_model=AdminLog,
    dependencies=[Depends(require_bot_token), Depends(require_admin_rate_limit)],
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
    "/unban",
    response_model=AdminLog,
    dependencies=[Depends(require_bot_token), Depends(require_admin_rate_limit)],
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


@router.post(
    "/check-batch",
    response_model=BatchCheckResponse,
    dependencies=[Depends(require_bot_token)],
)
async def batch_check_players(
    request: BatchCheckRequest, db: AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Batch check bans and timeouts for multiple players. Bot only.

    Returns dictionaries mapping discord_id to boolean status.
    """
    bans: Dict[str, bool] = {}
    timeouts: Dict[str, bool] = {}

    # Fetch all bans in one query
    if request.discord_ids:
        ban_docs = await db.admin_logs.find(
            {"action": "ban", "target_discord_id": {"$in": request.discord_ids}}
        ).to_list(length=len(request.discord_ids))
        banned_ids = {doc["target_discord_id"] for doc in ban_docs}
        bans = {
            discord_id: discord_id in banned_ids for discord_id in request.discord_ids
        }

        # Fetch all timeouts in one query
        timeout_docs = (
            await db.admin_logs.find(
                {"action": "timeout", "target_discord_id": {"$in": request.discord_ids}}
            )
            .sort("timestamp", -1)
            .to_list(length=len(request.discord_ids) * 2)
        )

        current_time = datetime.now(timezone.utc)

        for discord_id in request.discord_ids:
            latest_timeout = None
            for doc in timeout_docs:
                if doc["target_discord_id"] == discord_id:
                    latest_timeout = doc
                    break

            if latest_timeout:
                timeout_time = latest_timeout["timestamp"]
                if timeout_time.tzinfo is None:
                    timeout_time = timeout_time.replace(tzinfo=timezone.utc)
                duration = latest_timeout["duration_minutes"]
                time_diff = (current_time - timeout_time).total_seconds() / 60.0
                timeouts[discord_id] = time_diff < duration
            else:
                timeouts[discord_id] = False

    return BatchCheckResponse(bans=bans, timeouts=timeouts)
