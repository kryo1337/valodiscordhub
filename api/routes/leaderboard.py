from fastapi import APIRouter, Depends, HTTPException, Body, Query, Request
from db import get_db
from auth import require_bot_token, get_request_origin
from models.leaderboard import Leaderboard, LeaderboardEntry
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List, Literal, Optional
from events.broadcast import broadcast_leaderboard_update

router = APIRouter(prefix="/leaderboard", tags=["leaderboard"])


@router.get("/", response_model=List[Leaderboard])
async def list_leaderboards(db: AsyncIOMotorDatabase = Depends(get_db)):
    """List all leaderboards."""
    cursor = db.leaderboards.find()
    return [Leaderboard(**doc) async for doc in cursor]


@router.get("/{rank_group}", response_model=Leaderboard)
async def get_leaderboard(
    rank_group: str,
    sort_by: str = Query(
        "points", description="Field to sort by (points, winrate, matches_played)"
    ),
    sort_order: Literal["asc", "desc"] = Query("desc", description="Sort order"),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Get leaderboard for a rank group with server-side sorting.

    - **rank_group**: One of iron-plat, dia-asc, imm-radiant
    - **sort_by**: Field to sort by (default: points)
    - **sort_order**: asc or desc (default: desc)
    """
    doc = await db.leaderboards.find_one({"rank_group": rank_group})
    if not doc:
        raise HTTPException(
            status_code=404,
            detail=f"Leaderboard for rank group '{rank_group}' was not found. It may not have been initialized yet.",
        )

    leaderboard = Leaderboard(**doc)

    # Server-side sorting
    valid_sort_fields = {"points", "winrate", "matches_played", "streak"}
    if sort_by not in valid_sort_fields:
        sort_by = "points"

    reverse = sort_order == "desc"
    leaderboard.players = sorted(
        leaderboard.players, key=lambda x: getattr(x, sort_by, 0), reverse=reverse
    )

    return leaderboard


@router.get("/{rank_group}/top", response_model=List[LeaderboardEntry])
async def get_top_players(
    rank_group: str,
    limit: int = Query(10, ge=1, le=100, description="Number of top players to return"),
    skip: int = Query(
        0, ge=0, description="Number of players to skip (for pagination)"
    ),
    sort_by: str = Query("points", description="Field to sort by"),
    sort_order: Literal["asc", "desc"] = Query("desc", description="Sort order"),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Get top players from a leaderboard with pagination.

    This endpoint returns only the player entries (not the full leaderboard),
    making it more efficient for displaying leaderboard pages.
    """
    doc = await db.leaderboards.find_one({"rank_group": rank_group})
    if not doc:
        raise HTTPException(
            status_code=404,
            detail=f"Leaderboard for rank group '{rank_group}' was not found.",
        )

    leaderboard = Leaderboard(**doc)

    # Server-side sorting
    valid_sort_fields = {"points", "winrate", "matches_played", "streak"}
    if sort_by not in valid_sort_fields:
        sort_by = "points"

    reverse = sort_order == "desc"
    sorted_players = sorted(
        leaderboard.players, key=lambda x: getattr(x, sort_by, 0), reverse=reverse
    )

    # Pagination
    return sorted_players[skip : skip + limit]


@router.get("/{rank_group}/count")
async def get_player_count(rank_group: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    """Get total number of players in a leaderboard."""
    doc = await db.leaderboards.find_one({"rank_group": rank_group})
    if not doc:
        raise HTTPException(
            status_code=404,
            detail=f"Leaderboard for rank group '{rank_group}' was not found.",
        )

    leaderboard = Leaderboard(**doc)
    return {"count": len(leaderboard.players)}


@router.get("/{rank_group}/player/{discord_id}")
async def get_player_rank(
    rank_group: str, discord_id: str, db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Get a specific player's rank position in the leaderboard."""
    doc = await db.leaderboards.find_one({"rank_group": rank_group})
    if not doc:
        raise HTTPException(
            status_code=404,
            detail=f"Leaderboard for rank group '{rank_group}' was not found.",
        )

    leaderboard = Leaderboard(**doc)

    # Sort by points (default ranking)
    sorted_players = sorted(leaderboard.players, key=lambda x: x.points, reverse=True)

    for i, player in enumerate(sorted_players, start=1):
        if player.discord_id == discord_id:
            return {
                "rank_position": i,
                "total_players": len(sorted_players),
                "player": player,
            }

    raise HTTPException(
        status_code=404,
        detail=f"Player '{discord_id}' was not found in the {rank_group} leaderboard.",
    )


@router.put(
    "/{rank_group}",
    response_model=Leaderboard,
    dependencies=[Depends(require_bot_token)],
)
async def update_leaderboard(
    rank_group: str,
    request: Request,
    leaderboard: Leaderboard = Body(...),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Update or create a leaderboard. Bot only."""
    result = await db.leaderboards.update_one(
        {"rank_group": rank_group}, {"$set": leaderboard.dict()}, upsert=True
    )
    doc = await db.leaderboards.find_one({"rank_group": rank_group})
    updated_leaderboard = Leaderboard(**doc)

    origin = get_request_origin(request)

    # Sort by points and get top 50 for the broadcast
    sorted_players = sorted(
        updated_leaderboard.players, key=lambda x: x.points, reverse=True
    )[:50]
    top_players = [p.dict() for p in sorted_players]

    await broadcast_leaderboard_update(
        rank_group=rank_group,
        top_players=top_players,
        origin=origin,
    )

    return updated_leaderboard
