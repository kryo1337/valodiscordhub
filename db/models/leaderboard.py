from pydantic import BaseModel, Field
from typing import List, Literal
from datetime import datetime, timezone


class LeaderboardEntry(BaseModel):
    discord_id: str
    riot_id: str
    rank: str
    points: int
    matches_played: int
    winrate: float
    streak: int = Field(default=0)


class Leaderboard(BaseModel):
    rank_group: Literal["iron-plat", "dia-asc", "imm1-radiant"]
    players: List[LeaderboardEntry]
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
