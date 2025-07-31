from fastapi import APIRouter, Depends, HTTPException, Query, Body
from db import get_db
from auth import require_bot_token
from models.player import Player
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List, Optional

router = APIRouter(prefix="/players", tags=["players"])

@router.get("/", response_model=List[Player])
async def list_players(skip: int = 0, limit: int = Query(10, ge=1, le=100), db: AsyncIOMotorDatabase = Depends(get_db)):
    cursor = db.players.find().skip(skip).limit(limit)
    return [Player(**doc) async for doc in cursor]

@router.post("/", response_model=Player, dependencies=[Depends(require_bot_token)])
async def create_player(player: Player = Body(...), db: AsyncIOMotorDatabase = Depends(get_db)):
    if await db.players.find_one({"discord_id": player.discord_id}):
        raise HTTPException(status_code=409, detail="Player already exists")
    await db.players.insert_one(player.dict())
    return player

@router.get("/{discord_id}", response_model=Player)
async def get_player(discord_id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    doc = await db.players.find_one({"discord_id": discord_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Player not found")
    return Player(**doc)

@router.patch("/{discord_id}", response_model=Player, dependencies=[Depends(require_bot_token)])
async def update_player(discord_id: str, update: dict = Body(...), db: AsyncIOMotorDatabase = Depends(get_db)):
    result = await db.players.update_one({"discord_id": discord_id}, {"$set": update})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Player not found")
    doc = await db.players.find_one({"discord_id": discord_id})
    return Player(**doc)