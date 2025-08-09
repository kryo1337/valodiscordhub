from fastapi import APIRouter, Depends, HTTPException, Query
from db import get_db
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List
from models.match import Match

router = APIRouter(prefix="/history", tags=["history"]) 

@router.get("/matches", response_model=List[Match])
async def get_recent_matches(limit: int = Query(10, ge=1, le=100), db: AsyncIOMotorDatabase = Depends(get_db)):
    cursor = db.matches.find({"result": {"$ne": "cancelled"}}).sort("created_at", -1).limit(limit)
    return [Match(**doc) async for doc in cursor]