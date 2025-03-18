from pydantic import BaseModel, Field


class Player(BaseModel):
    discord_id: str
    riot_id: str
    rank: str
    points: int = Field(default=0)
    matches_played: int = Field(default=0)
    wins: int = Field(default=0)
    losses: int = Field(default=0)
    winrate: float = Field(default=0.0)
