from pydantic import BaseModel, Field
from typing import List, Literal
from datetime import datetime, timezone


class QueueEntry(BaseModel):
    discord_id: str
    joined_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Queue(BaseModel):
    rank_group: Literal["iron-plat", "dia-asc", "imm-radiant"]
    players: List[QueueEntry] = Field(default_factory=list)
