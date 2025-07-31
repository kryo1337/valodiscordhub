from fastapi import APIRouter, Depends, HTTPException, Body
from db import get_db
from auth import require_bot_token
from models.leaderboard import Leaderboard
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List

router = APIRouter(prefix="/leaderboard", tags=["leaderboard"])

@router.get("/", response_model=List[Leaderboard])
async def list_leaderboards(db: AsyncIOMotorDatabase = Depends(get_db)):
    cursor = db.leaderboards.find()
    return [Leaderboard(**doc) async for doc in cursor]

@router.get("/{rank_group}", response_model=Leaderboard)
async def get_leaderboard(rank_group: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    doc = await db.leaderboards.find_one({"rank_group": rank_group})
    if not doc:
        raise HTTPException(status_code=404, detail="Leaderboard not found")
    return Leaderboard(**doc)

@router.put("/{rank_group}", response_model=Leaderboard, dependencies=[Depends(require_bot_token)])
async def update_leaderboard(rank_group: str, leaderboard: Leaderboard = Body(...), db: AsyncIOMotorDatabase = Depends(get_db)):
    result = await db.leaderboards.update_one(
        {"rank_group": rank_group},
        {"$set": leaderboard.dict()},
        upsert=True
    )
    doc = await db.leaderboards.find_one({"rank_group": rank_group})
    return Leaderboard(**doc)