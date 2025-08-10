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

@router.get("/matches/all", response_model=List[Match])
async def get_all_matches(limit: int = Query(10, ge=1, le=100), db: AsyncIOMotorDatabase = Depends(get_db)):
    cursor = db.matches.find().sort("created_at", -1).limit(limit)
    return [Match(**doc) async for doc in cursor]

@router.get("/matches/player/{discord_id}", response_model=List[Match])
async def get_player_matches(
    discord_id: str, 
    limit: int = Query(10, ge=1, le=100), 
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    cursor = db.matches.find({
        "$or": [
            {"players_red": {"$in": [discord_id]}},
            {"players_blue": {"$in": [discord_id]}}
        ],
        "result": {"$ne": "cancelled"}
    }).sort("created_at", -1).limit(limit)
    return [Match(**doc) async for doc in cursor]