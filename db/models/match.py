from pydantic import BaseModel, Field, computed_field
from typing import List, Optional, Literal
from datetime import datetime, timezone, timedelta


class Match(BaseModel):
    match_id: str
    players_red: List[str]
    players_blue: List[str]
    captain_red: str
    captain_blue: str
    lobby_master: str
    defense_start: Optional[Literal["red", "blue"]] = None
    red_score: Optional[int] = None
    blue_score: Optional[int] = None
    result: Optional[Literal["red", "blue", "cancelled"]] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    ended_at: Optional[datetime] = None

    @computed_field
    @property
    def duration(self) -> Optional[timedelta]:
        if self.ended_at:
            return self.ended_at - self.created_at
        return None
