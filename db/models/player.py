from pydantic import BaseModel, Field, validator


class Player(BaseModel):
    discord_id: str
    riot_id: str
    rank: str
    points: int = Field(default=1000, ge=0)
    matches_played: int = Field(default=0, ge=0)
    wins: int = Field(default=0, ge=0)
    losses: int = Field(default=0, ge=0)
    winrate: float = Field(default=0.0, ge=0.0, le=100.0)

    @validator("winrate")
    def calculate_winrate(cls, v, values):
        if "matches_played" in values and values["matches_played"] > 0:
            return (values["wins"] / values["matches_played"]) * 100
        return 0.0
