from fastapi import APIRouter, Depends, HTTPException, Body, Request
from db import get_db
from auth import require_bot_token, get_request_origin
from models.queue import Queue, QueueEntry
from motor.motor_asyncio import AsyncIOMotorDatabase
from events.broadcast import broadcast_queue_update

router = APIRouter(prefix="/queue", tags=["queue"])


async def is_player_banned(discord_id: str, db: AsyncIOMotorDatabase) -> bool:
    doc = await db.admin_logs.find_one(
        {"action": "ban", "target_discord_id": discord_id}
    )
    return bool(doc)


async def is_player_timeout(discord_id: str, db: AsyncIOMotorDatabase) -> bool:
    from datetime import datetime, timezone

    # Check only the latest timeout log
    cursor = (
        db.admin_logs.find({"action": "timeout", "target_discord_id": discord_id})
        .sort("timestamp", -1)
        .limit(1)
    )
    try:
        timeout = await cursor.to_list(length=1)
        if not timeout:
            return False
        timeout = timeout[0]
    except Exception:
        return False

    timeout_time = timeout["timestamp"]
    if timeout_time.tzinfo is None:
        timeout_time = timeout_time.replace(tzinfo=timezone.utc)
    duration = timeout["duration_minutes"]
    current_time = datetime.now(timezone.utc)

    time_diff = (current_time - timeout_time).total_seconds() / 60.0

    # Do not delete expired timeouts, just return False
    return time_diff < duration


async def is_player_in_match(discord_id: str, db: AsyncIOMotorDatabase) -> bool:
    match = await db.matches.find_one(
        {
            "result": None,
            "$or": [{"players_red": discord_id}, {"players_blue": discord_id}],
        }
    )
    return bool(match)


@router.get("/{rank_group}", response_model=Queue)
async def get_queue(rank_group: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    doc = await db.queues.find_one({"rank_group": rank_group})
    if not doc:
        raise HTTPException(status_code=404, detail="Queue not found")
    return Queue(**doc)


@router.post(
    "/{rank_group}/join",
    response_model=Queue,
    dependencies=[Depends(require_bot_token)],
)
async def join_queue(
    rank_group: str,
    request: Request,
    entry: QueueEntry = Body(...),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    if await is_player_banned(entry.discord_id, db):
        raise HTTPException(
            status_code=403, detail="You are banned from the queue system"
        )

    if await is_player_timeout(entry.discord_id, db):
        raise HTTPException(
            status_code=403, detail="You are in timeout and cannot join the queue"
        )

    if await is_player_in_match(entry.discord_id, db):
        raise HTTPException(
            status_code=403,
            detail="You are currently in an active match and cannot join the queue",
        )

    # Atomic update to prevent race conditions
    # Uses find_one_and_update with conditions to ensure:
    # 1. Player is not already in queue
    # 2. Queue has less than 10 players
    result = await db.queues.find_one_and_update(
        {
            "rank_group": rank_group,
            "$expr": {
                "$and": [
                    {
                        "$not": {
                            "$in": [
                                entry.discord_id,
                                {
                                    "$map": {
                                        "input": "$players",
                                        "as": "p",
                                        "in": "$$p.discord_id",
                                    }
                                },
                            ]
                        }
                    },
                    {"$lt": [{"$size": "$players"}, 10]},
                ]
            },
        },
        {"$push": {"players": entry.dict()}},
        return_document=True,
        upsert=True,
    )

    if not result:
        # The update failed - check why
        queue_doc = await db.queues.find_one({"rank_group": rank_group})
        if queue_doc:
            if any(
                p["discord_id"] == entry.discord_id
                for p in queue_doc.get("players", [])
            ):
                raise HTTPException(status_code=400, detail="You are already in queue")
            if len(queue_doc.get("players", [])) >= 10:
                raise HTTPException(
                    status_code=400, detail="Queue is full (10/10 players)"
                )
        else:
            # Shouldn't happen with upsert, but handle gracefully
            raise HTTPException(status_code=500, detail="Failed to join queue")

    doc = await db.queues.find_one({"rank_group": rank_group})
    queue = Queue(**doc)

    origin = get_request_origin(request)

    await broadcast_queue_update(
        rank_group=rank_group,
        action="joined",
        discord_id=entry.discord_id,
        players=[p.discord_id for p in queue.players],
        queue_count=len(queue.players),
        origin=origin,
        origin_id=entry.discord_id,
    )

    return queue


@router.post(
    "/{rank_group}/leave",
    response_model=Queue,
    dependencies=[Depends(require_bot_token)],
)
async def leave_queue(
    rank_group: str,
    request: Request,
    entry: QueueEntry = Body(...),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    result = await db.queues.update_one(
        {"rank_group": rank_group},
        {"$pull": {"players": {"discord_id": entry.discord_id}}},
    )
    doc = await db.queues.find_one({"rank_group": rank_group})
    queue = Queue(**doc)

    origin = get_request_origin(request)

    await broadcast_queue_update(
        rank_group=rank_group,
        action="left",
        discord_id=entry.discord_id,
        players=[p.discord_id for p in queue.players],
        queue_count=len(queue.players),
        origin=origin,
        origin_id=entry.discord_id,
    )

    return queue


@router.put(
    "/{rank_group}", response_model=Queue, dependencies=[Depends(require_bot_token)]
)
async def update_queue(
    rank_group: str,
    request: Request,
    queue: Queue = Body(...),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    result = await db.queues.update_one(
        {"rank_group": rank_group}, {"$set": queue.dict()}, upsert=True
    )
    doc = await db.queues.find_one({"rank_group": rank_group})
    updated_queue = Queue(**doc)

    origin = get_request_origin(request)

    await broadcast_queue_update(
        rank_group=rank_group,
        action="joined",  # Generic update treated as join for full queue replacement
        players=[p.discord_id for p in updated_queue.players],
        queue_count=len(updated_queue.players),
        origin=origin,
    )

    return updated_queue


@router.delete("/{rank_group}", dependencies=[Depends(require_bot_token)])
async def clear_queue(
    rank_group: str, request: Request, db: AsyncIOMotorDatabase = Depends(get_db)
):
    await db.queues.update_one(
        {"rank_group": rank_group}, {"$set": {"players": []}}, upsert=True
    )
    doc = await db.queues.find_one({"rank_group": rank_group})

    origin = get_request_origin(request)

    await broadcast_queue_update(
        rank_group=rank_group,
        action="cleared",
        players=[],
        queue_count=0,
        origin=origin,
    )

    return Queue(**doc)
