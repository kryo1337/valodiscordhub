from fastapi import APIRouter, Depends, HTTPException, Query, Body, Request
from db import get_db
from auth import require_bot_token, get_request_origin
from models.match import Match
from models.updates import MatchUpdate
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List
from events.broadcast import (
    broadcast_match_created,
    broadcast_match_updated,
    broadcast_match_result,
)

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
async def create_match(
    request: Request,
    match: Match = Body(...),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    if await db.matches.find_one({"match_id": match.match_id}):
        raise HTTPException(status_code=409, detail="Match already exists")
    await db.matches.insert_one(match.dict())

    origin = get_request_origin(request)

    await broadcast_match_created(
        match_id=match.match_id,
        rank_group=match.rank_group,
        players_red=match.players_red,
        players_blue=match.players_blue,
        captain_red=match.captain_red,
        captain_blue=match.captain_blue,
        origin=origin,
    )

    return match


@router.get("/{match_id}", response_model=Match)
async def get_match(match_id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    doc = await db.matches.find_one({"match_id": match_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Match not found")
    return Match(**doc)


@router.patch(
    "/{match_id}", response_model=Match, dependencies=[Depends(require_bot_token)]
)
async def update_match(
    match_id: str,
    request: Request,
    update: MatchUpdate = Body(...),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    update_dict = update.get_update_dict()
    if not update_dict:
        raise HTTPException(status_code=400, detail="No valid fields to update")
    result = await db.matches.update_one({"match_id": match_id}, {"$set": update_dict})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Match not found")
    doc = await db.matches.find_one({"match_id": match_id})
    match = Match(**doc)

    origin = get_request_origin(request)

    # Determine update type and broadcast accordingly
    if "result" in update_dict:
        # Match has a result - broadcast match result event
        if match.result:  # Ensure result is not None
            await broadcast_match_result(
                match_id=match_id,
                result=match.result,
                red_score=match.red_score,
                blue_score=match.blue_score,
                rank_group=match.rank_group,
                origin=origin,
            )
    else:
        # Determine update type based on fields changed
        update_type = _determine_update_type(update_dict)
        await broadcast_match_updated(
            match_id=match_id,
            update_type=update_type,
            data=update_dict,
            rank_group=match.rank_group,
            origin=origin,
        )

    return match


def _determine_update_type(update_dict: dict) -> str:
    """Determine the update type based on the fields being updated."""
    if "players_red" in update_dict or "players_blue" in update_dict:
        return "teams"
    elif "captain_red" in update_dict or "captain_blue" in update_dict:
        return "captains"
    elif "selected_map" in update_dict or "banned_maps" in update_dict:
        return "draft"
    elif "red_score" in update_dict or "blue_score" in update_dict:
        return "score"
    else:
        return "teams"  # Default fallback
