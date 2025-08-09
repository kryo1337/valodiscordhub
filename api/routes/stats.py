from fastapi import APIRouter, Depends, HTTPException, Query
from db import get_db
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import Optional, Literal

router = APIRouter(prefix="/stats", tags=["stats"]) 

RankGroup = Literal["iron-plat", "dia-asc", "imm-radiant"]

@router.get("/{discord_id}")
async def get_player_stats(
    discord_id: str,
    rank_group: Optional[RankGroup] = None,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    groups = [rank_group] if rank_group else ["iron-plat", "dia-asc", "imm-radiant"]
    lb_entry = None
    resolved_group: Optional[str] = None
    for g in groups:
        doc = await db.leaderboards.find_one({"rank_group": g})
        if not doc or "players" not in doc:
            continue
        for p in doc["players"]:
            if p.get("discord_id") == discord_id:
                lb_entry = p
                resolved_group = g
                break
        if lb_entry:
            break

    wins = 0
    losses = 0
    total = 0
    async for m in db.matches.find({"$or": [
        {"players_red": discord_id},
        {"players_blue": discord_id}
    ]}):
        # normalize players list search above; motor won't match scalar in array unless equality; we need $in
        pass

    async for m in db.matches.find({"$or": [
        {"players_red": {"$in": [discord_id]}},
        {"players_blue": {"$in": [discord_id]}}
    ]}):
        result = m.get("result")
        if result is None or result == "cancelled":
            continue
        is_red = discord_id in m.get("players_red", [])
        is_blue = discord_id in m.get("players_blue", [])
        if not (is_red or is_blue):
            continue
        total += 1
        if (result == "red" and is_red) or (result == "blue" and is_blue):
            wins += 1
        else:
            losses += 1

    winrate = (wins / total * 100.0) if total > 0 else 0.0

    player_doc = await db.players.find_one({"discord_id": discord_id})

    return {
        "discord_id": discord_id,
        "rank_group": resolved_group,
        "rank": (player_doc or {}).get("rank"),
        "points": (lb_entry or {}).get("points"),
        "matches_played": total,
        "wins": wins,
        "losses": losses,
        "winrate": round(winrate, 2),
        "streak": (lb_entry or {}).get("streak"),
    }