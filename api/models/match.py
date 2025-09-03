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
    rank_group: Literal["iron-plat", "dia-asc", "imm-radiant"]
    defense_start: Optional[Literal["red", "blue"]] = None
    banned_maps: List[str] = Field(default_factory=list)
    selected_map: Optional[str] = None
    red_score: Optional[int] = None
    blue_score: Optional[int] = None
    result: Optional[Literal["red", "blue", "cancelled"]] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    ended_at: Optional[datetime] = None

    @computed_field
    @property
    def duration(self) -> Optional[timedelta]:
        if not self.ended_at:
            return None

        def ensure_aware_utc(dt: datetime) -> datetime:
            if dt.tzinfo is None:
                return dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)

        ended_at_aware = ensure_aware_utc(self.ended_at)
        created_at_aware = ensure_aware_utc(self.created_at)
        return ended_at_aware - created_at_aware
