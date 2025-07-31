from fastapi import APIRouter, Depends, HTTPException, Body
from db import get_db
from auth import require_bot_token
from models.preferences import UserPreferences
from motor.motor_asyncio import AsyncIOMotorDatabase

router = APIRouter(prefix="/preferences", tags=["preferences"])

@router.get("/{discord_id}", response_model=UserPreferences)
async def get_preferences(discord_id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    doc = await db.preferences.find_one({"discord_id": discord_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Preferences not found")
    return UserPreferences(**doc)

@router.patch("/{discord_id}", response_model=UserPreferences, dependencies=[Depends(require_bot_token)])
async def update_preferences(discord_id: str, update: dict = Body(...), db: AsyncIOMotorDatabase = Depends(get_db)):
    result = await db.preferences.update_one({"discord_id": discord_id}, {"$set": update})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Preferences not found")
    doc = await db.preferences.find_one({"discord_id": discord_id})
    return UserPreferences(**doc)