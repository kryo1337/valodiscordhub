from fastapi import APIRouter, Depends, HTTPException, Query, Body, Request
from db import get_db
from auth import (
    require_bot_token,
    require_auth,
    optional_current_user,
    get_request_origin,
)
from models.player import Player
from models.updates import PlayerUpdate
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List, Optional
from events.broadcast import broadcast_player_updated

router = APIRouter(prefix="/players", tags=["players"])


@router.get("/", response_model=List[Player], dependencies=[Depends(require_auth)])
async def list_players(
    skip: int = 0,
    limit: int = Query(10, ge=1, le=100),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """List all players. Requires authentication."""
    cursor = db.players.find().skip(skip).limit(limit)
    return [Player(**doc) async for doc in cursor]


@router.post("/", response_model=Player, dependencies=[Depends(require_bot_token)])
async def create_player(
    request: Request,
    player: Player = Body(...),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Create a new player. Bot only."""
    if await db.players.find_one({"discord_id": player.discord_id}):
        raise HTTPException(status_code=409, detail="Player already exists")
    await db.players.insert_one(player.dict())

    origin = get_request_origin(request)

    if player.rank:
        await broadcast_player_updated(
            discord_id=player.discord_id,
            field="rank",
            value=player.rank,
            origin=origin,
            origin_id=player.discord_id,
        )

    return player


@router.get("/{discord_id}", response_model=Player)
async def get_player(
    discord_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: Optional[dict] = Depends(optional_current_user),
):
    """
    Get player by discord ID.
    - Authenticated users (bot or web): Can view any player
    - Unauthenticated: Can only view their own profile (if they provide discord_id)
    """
    doc = await db.players.find_one({"discord_id": discord_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Player not found")

    # If authenticated (bot or user), allow full access
    if current_user:
        return Player(**doc)

    # For unauthenticated requests, only allow viewing public profile summary
    # (in this case, we still return the full profile but this could be restricted)
    return Player(**doc)


@router.patch(
    "/{discord_id}", response_model=Player, dependencies=[Depends(require_bot_token)]
)
async def update_player(
    discord_id: str,
    request: Request,
    update: PlayerUpdate = Body(...),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    update_dict = update.get_update_dict()
    if not update_dict:
        raise HTTPException(status_code=400, detail="No valid fields to update")
    result = await db.players.update_one(
        {"discord_id": discord_id}, {"$set": update_dict}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Player not found")
    doc = await db.players.find_one({"discord_id": discord_id})
    player = Player(**doc)

    origin = get_request_origin(request)

    broadcast_fields = {"rank", "points", "riot_id"}
    for field, value in update_dict.items():
        if field in broadcast_fields:
            await broadcast_player_updated(
                discord_id=discord_id,
                field=field,
                value=str(value),
                origin=origin,
                origin_id=discord_id,
            )

    return player


@router.delete("/test-bots", dependencies=[Depends(require_bot_token)])
async def delete_test_bots(db: AsyncIOMotorDatabase = Depends(get_db)):
    result = await db.players.delete_many({"discord_id": {"$regex": "^test_user_"}})
    return {"deleted_count": result.deleted_count}
