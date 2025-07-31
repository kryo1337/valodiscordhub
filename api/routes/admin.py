from fastapi import APIRouter, Depends, HTTPException, Query, Body
from db import get_db
from auth import require_bot_token
from models.admin_log import AdminLog
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List, Optional
from datetime import datetime, timezone

router = APIRouter(prefix="/admin", tags=["admin"])

@router.get("/logs", response_model=List[AdminLog])
async def list_admin_logs(
    action: Optional[str] = None,
    admin_discord_id: Optional[str] = None,
    target_discord_id: Optional[str] = None,
    match_id: Optional[str] = None,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    query = {}
    if action:
        query["action"] = action
    if admin_discord_id:
        query["admin_discord_id"] = admin_discord_id
    if target_discord_id:
        query["target_discord_id"] = target_discord_id
    if match_id:
        query["match_id"] = match_id
    cursor = db.admin_logs.find(query).sort("timestamp", -1)
    return [AdminLog(**doc) async for doc in cursor]

@router.get("/bans", response_model=List[dict])
async def get_banned_players(db: AsyncIOMotorDatabase = Depends(get_db)):
    cursor = db.admin_logs.find(
        {"action": "ban", "target_discord_id": {"$exists": True}},
        {"target_discord_id": 1, "reason": 1, "timestamp": 1}
    )
    return [doc async for doc in cursor]

@router.get("/timeouts", response_model=List[dict])
async def get_timeout_players(db: AsyncIOMotorDatabase = Depends(get_db)):
    cursor = db.admin_logs.find(
        {"action": "timeout", "target_discord_id": {"$exists": True}},
        {"target_discord_id": 1, "reason": 1, "duration_minutes": 1, "timestamp": 1}
    )
    return [doc async for doc in cursor]

@router.get("/check-ban/{discord_id}", response_model=bool)
async def is_player_banned(discord_id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    doc = await db.admin_logs.find_one({"action": "ban", "target_discord_id": discord_id})
    return bool(doc)

@router.get("/check-timeout/{discord_id}", response_model=bool)
async def is_player_timeout(discord_id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
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

@router.delete("/logs/{action}/{target_discord_id}", dependencies=[Depends(require_bot_token)])
async def remove_admin_log(action: str, target_discord_id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    result = await db.admin_logs.delete_one({"action": action, "target_discord_id": target_discord_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Admin log not found")
    return {"message": "Admin log removed"}

@router.post("/ban", response_model=AdminLog, dependencies=[Depends(require_bot_token)])
async def ban_player(log: AdminLog = Body(...), db: AsyncIOMotorDatabase = Depends(get_db)):
    log_dict = log.dict()
    log_dict["timestamp"] = datetime.now(timezone.utc)
    log_dict["action"] = "ban"
    await db.admin_logs.insert_one(log_dict)
    return AdminLog(**log_dict)

@router.post("/timeout", response_model=AdminLog, dependencies=[Depends(require_bot_token)])
async def timeout_player(log: AdminLog = Body(...), db: AsyncIOMotorDatabase = Depends(get_db)):
    log_dict = log.dict()
    log_dict["timestamp"] = datetime.now(timezone.utc)
    log_dict["action"] = "timeout"
    await db.admin_logs.insert_one(log_dict)
    return AdminLog(**log_dict)

@router.post("/unban", response_model=AdminLog, dependencies=[Depends(require_bot_token)])
async def unban_player(log: AdminLog = Body(...), db: AsyncIOMotorDatabase = Depends(get_db)):
    log_dict = log.dict()
    log_dict["timestamp"] = datetime.now(timezone.utc)
    log_dict["action"] = "unban"
    await db.admin_logs.insert_one(log_dict)
    return AdminLog(**log_dict)