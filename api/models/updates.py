"""
Update models for PATCH endpoints.
These models define what fields can be updated and their constraints.
All fields are optional since PATCH allows partial updates.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Literal
from datetime import datetime


# Valid Valorant ranks for validation
VALID_RANKS = [
    "iron1",
    "iron2",
    "iron3",
    "bronze1",
    "bronze2",
    "bronze3",
    "silver1",
    "silver2",
    "silver3",
    "gold1",
    "gold2",
    "gold3",
    "platinum1",
    "platinum2",
    "platinum3",
    "diamond1",
    "diamond2",
    "diamond3",
    "ascendant1",
    "ascendant2",
    "ascendant3",
    "immortal1",
    "immortal2",
    "immortal3",
    "radiant",
]

# Valid rank groups
VALID_RANK_GROUPS = ["iron-plat", "dia-asc", "imm-radiant"]


class PlayerUpdate(BaseModel):
    """Model for updating player data via PATCH /players/{discord_id}"""

    riot_id: Optional[str] = Field(
        default=None,
        min_length=3,
        max_length=50,
        description="Player's Riot ID (format: Name#TAG)",
    )
    rank: Optional[str] = Field(default=None, description="Player's Valorant rank")
    points: Optional[int] = Field(
        default=None, ge=0, le=99999, description="Player's leaderboard points"
    )
    matches_played: Optional[int] = Field(
        default=None, ge=0, description="Total matches played"
    )
    wins: Optional[int] = Field(default=None, ge=0, description="Total wins")
    losses: Optional[int] = Field(default=None, ge=0, description="Total losses")
    winrate: Optional[float] = Field(
        default=None, ge=0.0, le=100.0, description="Win rate percentage"
    )

    @field_validator("rank")
    @classmethod
    def validate_rank(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v.lower() not in VALID_RANKS:
            raise ValueError(
                f"Invalid rank '{v}'. Must be one of: {', '.join(VALID_RANKS)}"
            )
        return v.lower() if v else None

    @field_validator("riot_id")
    @classmethod
    def validate_riot_id(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and "#" not in v:
            raise ValueError("Riot ID must be in format 'Name#TAG'")
        return v

    def get_update_dict(self) -> dict:
        """Get only the fields that were explicitly set (not None)."""
        return {k: v for k, v in self.model_dump().items() if v is not None}


class MatchUpdate(BaseModel):
    """Model for updating match data via PATCH /matches/{match_id}"""

    players_red: Optional[List[str]] = Field(
        default=None, max_length=5, description="Red team player discord IDs"
    )
    players_blue: Optional[List[str]] = Field(
        default=None, max_length=5, description="Blue team player discord IDs"
    )
    captain_red: Optional[str] = Field(
        default=None, description="Red team captain discord ID"
    )
    captain_blue: Optional[str] = Field(
        default=None, description="Blue team captain discord ID"
    )
    defense_start: Optional[Literal["red", "blue"]] = Field(
        default=None, description="Which team starts on defense"
    )
    banned_maps: Optional[List[str]] = Field(
        default=None, max_length=10, description="List of banned map names"
    )
    selected_map: Optional[str] = Field(
        default=None, max_length=50, description="Selected map name"
    )
    red_score: Optional[int] = Field(
        default=None, ge=0, le=99, description="Red team score"
    )
    blue_score: Optional[int] = Field(
        default=None, ge=0, le=99, description="Blue team score"
    )
    result: Optional[Literal["red", "blue", "cancelled"]] = Field(
        default=None, description="Match result"
    )
    ended_at: Optional[datetime] = Field(
        default=None, description="When the match ended (UTC)"
    )

    @field_validator("players_red", "players_blue")
    @classmethod
    def validate_team_size(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v is not None and len(v) > 5:
            raise ValueError("Team cannot have more than 5 players")
        return v

    def get_update_dict(self) -> dict:
        """Get only the fields that were explicitly set (not None)."""
        data = {}
        for k, v in self.model_dump().items():
            if v is not None:
                # Handle datetime serialization
                if isinstance(v, datetime):
                    data[k] = v.isoformat()
                else:
                    data[k] = v
        return data


class AdminLogCreate(BaseModel):
    """Model for creating admin logs with validation."""

    action: Literal[
        "ban",
        "cancel_match",
        "revert_match",
        "timeout",
        "unban",
        "set_rank",
        "set_points",
        "set_result",
        "setup_queue",
        "refresh_all",
    ] = Field(..., description="Type of admin action")

    admin_discord_id: str = Field(
        ...,
        min_length=17,
        max_length=20,
        description="Discord ID of admin performing action",
    )
    target_discord_id: Optional[str] = Field(
        default=None,
        min_length=17,
        max_length=20,
        description="Discord ID of target player",
    )
    match_id: Optional[str] = Field(
        default=None, max_length=50, description="Match ID if action is match-related"
    )
    reason: Optional[str] = Field(
        default=None, max_length=500, description="Reason for the action"
    )
    duration_minutes: Optional[int] = Field(
        default=None,
        ge=1,
        le=525600,  # 1 year max
        description="Duration in minutes (for timeouts)",
    )

    @field_validator("admin_discord_id", "target_discord_id")
    @classmethod
    def validate_discord_id(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if not v.isdigit():
                raise ValueError("Discord ID must contain only digits")
        return v
