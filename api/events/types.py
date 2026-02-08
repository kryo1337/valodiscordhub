"""
Pydantic models for WebSocket event types.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Literal, Dict, Any
from datetime import datetime, timezone

# Origin types for event deduplication
EventOrigin = Literal["bot", "frontend"]


class BaseEvent(BaseModel):
    """Base event structure."""

    type: str = Field(..., description="Event type")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Event timestamp in UTC",
    )
    origin: EventOrigin = Field(
        default="frontend",
        description="Source that triggered this event (bot or frontend)",
    )
    origin_id: Optional[str] = Field(
        None,
        description="Discord ID of the user who triggered this event",
    )


class QueueUpdateEvent(BaseEvent):
    """Event for queue changes."""

    type: Literal["queue_update"] = "queue_update"
    rank_group: str = Field(..., description="The rank group of the queue")
    action: Literal["joined", "left", "cleared"] = Field(
        ..., description="The action that occurred"
    )
    discord_id: Optional[str] = Field(
        None, description="Discord ID of the player (if applicable)"
    )
    queue_count: int = Field(..., description="Current number of players in queue")
    players: List[str] = Field(
        default_factory=list, description="List of player discord IDs in queue"
    )


class MatchCreatedEvent(BaseEvent):
    """Event for new match creation."""

    type: Literal["match_created"] = "match_created"
    match_id: str = Field(..., description="Unique match identifier")
    rank_group: str = Field(..., description="The rank group of the match")
    players_red: List[str] = Field(..., description="Discord IDs of red team players")
    players_blue: List[str] = Field(..., description="Discord IDs of blue team players")
    captain_red: str = Field(..., description="Discord ID of red team captain")
    captain_blue: str = Field(..., description="Discord ID of blue team captain")


class MatchUpdatedEvent(BaseEvent):
    """Event for match updates."""

    type: Literal["match_updated"] = "match_updated"
    match_id: str = Field(..., description="Unique match identifier")
    update_type: Literal["teams", "captains", "draft", "score", "cancelled"] = Field(
        ..., description="Type of update"
    )
    data: Dict[str, Any] = Field(
        default_factory=dict, description="Update data payload"
    )


class MatchResultEvent(BaseEvent):
    """Event for match completion."""

    type: Literal["match_result"] = "match_result"
    match_id: str = Field(..., description="Unique match identifier")
    result: Literal["red", "blue", "cancelled"] = Field(..., description="Match result")
    red_score: Optional[int] = Field(None, description="Red team score")
    blue_score: Optional[int] = Field(None, description="Blue team score")


class LeaderboardUpdateEvent(BaseEvent):
    """Event for leaderboard changes."""

    type: Literal["leaderboard_update"] = "leaderboard_update"
    rank_group: str = Field(..., description="The rank group of the leaderboard")
    top_players: List[Dict[str, Any]] = Field(
        default_factory=list, description="List of top player data"
    )


class PlayerUpdatedEvent(BaseEvent):
    """Event for player data changes."""

    type: Literal["player_updated"] = "player_updated"
    discord_id: str = Field(..., description="Discord ID of the player")
    field: Literal["rank", "points", "riot_id"] = Field(
        ..., description="Field that was updated"
    )
    value: str = Field(..., description="New value of the field")
