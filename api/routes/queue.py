from fastapi import APIRouter, Depends, HTTPException, Body
from db import get_db
from auth import require_bot_token
from models.queue import Queue, QueueEntry
from motor.motor_asyncio import AsyncIOMotorDatabase

router = APIRouter(prefix="/queue", tags=["queue"])

@router.get("/{rank_group}", response_model=Queue)
async def get_queue(rank_group: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    doc = await db.queues.find_one({"rank_group": rank_group})
    if not doc:
        raise HTTPException(status_code=404, detail="Queue not found")
    return Queue(**doc)

@router.post("/{rank_group}/join", response_model=Queue, dependencies=[Depends(require_bot_token)])
async def join_queue(rank_group: str, entry: QueueEntry = Body(...), db: AsyncIOMotorDatabase = Depends(get_db)):
    result = await db.queues.update_one(
        {"rank_group": rank_group},
        {"$addToSet": {"players": entry.dict()}},
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