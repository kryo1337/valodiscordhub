from fastapi import APIRouter, Depends, HTTPException, Body
from db import get_db
from auth import require_bot_token
from models.queue import Queue, QueueEntry
from motor.motor_asyncio import AsyncIOMotorDatabase

router = APIRouter(prefix="/queue", tags=["queue"])

async def is_player_banned(discord_id: str, db: AsyncIOMotorDatabase) -> bool:
    doc = await db.admin_logs.find_one({"action": "ban", "target_discord_id": discord_id})
    return bool(doc)

async def is_player_timeout(discord_id: str, db: AsyncIOMotorDatabase) -> bool:
    from datetime import datetime, timezone
    timeout = await db.admin_logs.find_one({"action": "timeout", "target_discord_id": discord_id})
    if not timeout:
        return False
    
    timeout_time = timeout["timestamp"]
    if timeout_time.tzinfo is None:
        timeout_time = timeout_time.replace(tzinfo=timezone.utc)
    duration = timeout["duration_minutes"]
    current_time = datetime.now(timezone.utc)
    
    time_diff = (current_time - timeout_time).total_seconds() / 60.0
    
    if time_diff >= duration:
        await db.admin_logs.delete_one({"action": "timeout", "target_discord_id": discord_id})
        return False
        
    return time_diff < duration

async def is_player_in_match(discord_id: str, db: AsyncIOMotorDatabase) -> bool:
    cursor = db.matches.find({"result": None})
    async for match in cursor:
        if discord_id in match.get("players_red", []) or discord_id in match.get("players_blue", []):
            return True
    return False

@router.get("/{rank_group}", response_model=Queue)
async def get_queue(rank_group: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    doc = await db.queues.find_one({"rank_group": rank_group})
    if not doc:
        raise HTTPException(status_code=404, detail="Queue not found")
    return Queue(**doc)

@router.post("/{rank_group}/join", response_model=Queue, dependencies=[Depends(require_bot_token)])
async def join_queue(rank_group: str, entry: QueueEntry = Body(...), db: AsyncIOMotorDatabase = Depends(get_db)):
    if await is_player_banned(entry.discord_id, db):
        raise HTTPException(status_code=403, detail="You are banned from the queue system")
    
    if await is_player_timeout(entry.discord_id, db):
        raise HTTPException(status_code=403, detail="You are in timeout and cannot join the queue")
    
    if await is_player_in_match(entry.discord_id, db):
        raise HTTPException(status_code=403, detail="You are currently in an active match and cannot join the queue")
    
    existing_queue = await db.queues.find_one({
        "rank_group": rank_group,
        "players": {"$elemMatch": {"discord_id": entry.discord_id}}
    })
    if existing_queue:
        raise HTTPException(status_code=400, detail="You are already in the queue")
    
    await db.queues.update_one(
        {"rank_group": rank_group},
        {"$push": {"players": entry.dict()}},
        upsert=True
    )
    doc = await db.queues.find_one({"rank_group": rank_group})
    return Queue(**doc)

@router.post("/{rank_group}/leave", response_model=Queue, dependencies=[Depends(require_bot_token)])
async def leave_queue(rank_group: str, entry: QueueEntry = Body(...), db: AsyncIOMotorDatabase = Depends(get_db)):
    result = await db.queues.update_one(
        {"rank_group": rank_group},
        {"$pull": {"players": {"discord_id": entry.discord_id}}}
    )
    doc = await db.queues.find_one({"rank_group": rank_group})
    return Queue(**doc)

@router.put("/{rank_group}", response_model=Queue, dependencies=[Depends(require_bot_token)])
async def update_queue(rank_group: str, queue: Queue = Body(...), db: AsyncIOMotorDatabase = Depends(get_db)):
    result = await db.queues.update_one(
        {"rank_group": rank_group},
        {"$set": queue.dict()},
        upsert=True
    )
    doc = await db.queues.find_one({"rank_group": rank_group})
    return Queue(**doc)

@router.delete("/{rank_group}", dependencies=[Depends(require_bot_token)])
async def clear_queue(rank_group: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    await db.queues.update_one(
        {"rank_group": rank_group},
        {"$set": {"players": []}},
        upsert=True
    )
    doc = await db.queues.find_one({"rank_group": rank_group})
    return Queue(**doc)