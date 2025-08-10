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
    player_doc = await db.players.find_one({"discord_id": discord_id})
    if not player_doc:
        raise HTTPException(status_code=404, detail="Player not found")
    
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

    return {
        "discord_id": discord_id,
        "rank_group": resolved_group,
        "rank": player_doc.get("rank"),
        "points": (lb_entry or {}).get("points", 1000),
        "matches_played": (lb_entry or {}).get("matches_played", 0),
        "wins": player_doc.get("wins", 0),
        "losses": player_doc.get("losses", 0),
        "winrate": (lb_entry or {}).get("winrate", 0.0),
        "streak": (lb_entry or {}).get("streak", 0),
    }