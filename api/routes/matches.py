from fastapi import APIRouter, Depends, HTTPException, Query, Body
from db import get_db
from auth import require_bot_token
from models.match import Match
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List

router = APIRouter(prefix="/matches", tags=["matches"])

@router.get("/next-id", dependencies=[Depends(require_bot_token)])
async def get_next_match_id(db: AsyncIOMotorDatabase = Depends(get_db)):
    cursor = db.matches.find({}, {"match_id": 1}).sort("_id", -1)
    highest_num = 0
    async for doc in cursor:
        match_id = doc.get("match_id", "")
        if match_id.startswith("match_"):
            try:
                num = int(match_id.split("_")[1])
                highest_num = max(highest_num, num)
            except (IndexError, ValueError):
                continue
    
    next_num = highest_num + 1
    return {"match_id": f"match_{next_num}"}

@router.get("/active", response_model=List[Match])
async def get_active_matches(db: AsyncIOMotorDatabase = Depends(get_db)):
    cursor = db.matches.find({"result": None})
    matches = [Match(**doc) async for doc in cursor]
    return matches

@router.post("/", response_model=Match, dependencies=[Depends(require_bot_token)])
async def create_match(match: Match = Body(...), db: AsyncIOMotorDatabase = Depends(get_db)):
    if await db.matches.find_one({"match_id": match.match_id}):
        raise HTTPException(status_code=409, detail="Match already exists")
    await db.matches.insert_one(match.dict())
    return match

@router.get("/{match_id}", response_model=Match)
async def get_match(match_id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    doc = await db.matches.find_one({"match_id": match_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Match not found")
    return Match(**doc)

@router.patch("/{match_id}", response_model=Match, dependencies=[Depends(require_bot_token)])
async def update_match(match_id: str, update: dict = Body(...), db: AsyncIOMotorDatabase = Depends(get_db)):
    result = await db.matches.update_one({"match_id": match_id}, {"$set": update})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Match not found")
    doc = await db.matches.find_one({"match_id": match_id})
    return Match(**doc)