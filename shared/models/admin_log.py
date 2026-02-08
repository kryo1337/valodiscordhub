from pydantic import BaseModel, Field
from typing import Literal, Optional
from datetime import datetime, timezone


class AdminLog(BaseModel):
    action: Literal[
        "ban",
        "cancel_match",
        "revert_match",
        "timeout",
        "set_rank",
        "set_points",
        "set_result",
        "setup_queue",
        "refresh_all",
    ]
    admin_discord_id: str
    target_discord_id: Optional[str] = None
    match_id: Optional[str] = None
    reason: Optional[str] = None
    duration_minutes: Optional[int] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
