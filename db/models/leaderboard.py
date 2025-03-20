from pydantic import BaseModel, Field
from typing import List, Literal
from datetime import datetime, timezone


class LeaderboardEntry(BaseModel):
    discord_id: str
    rank: str
    points: int = Field(ge=0)
    matches_played: int = Field(ge=0)
    winrate: float = Field(ge=0.0, le=100.0)
    streak: int = Field(default=0)


class Leaderboard(BaseModel):
    rank_group: Literal["iron-plat", "dia-asc", "imm1-radiant"]
    players: List[LeaderboardEntry] = Field(default_factory=list)
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def get_top_players(self, limit: int = 10) -> List[LeaderboardEntry]:
        return sorted(self.players, key=lambda x: x.points, reverse=True)[:limit]
