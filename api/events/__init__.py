"""
Event types and broadcasting utilities for WebSocket.
"""

from events.types import (
    EventOrigin,
    BaseEvent,
    QueueUpdateEvent,
    MatchCreatedEvent,
    MatchUpdatedEvent,
    MatchResultEvent,
    LeaderboardUpdateEvent,
    PlayerUpdatedEvent,
)

from events.broadcast import (
    broadcast_queue_update,
    broadcast_match_created,
    broadcast_match_updated,
    broadcast_match_result,
    broadcast_leaderboard_update,
    broadcast_player_updated,
)

__all__ = [
    # Event origin type
    "EventOrigin",
    # Event types
    "BaseEvent",
    "QueueUpdateEvent",
    "MatchCreatedEvent",
    "MatchUpdatedEvent",
    "MatchResultEvent",
    "LeaderboardUpdateEvent",
    "PlayerUpdatedEvent",
    # Broadcast functions
    "broadcast_queue_update",
    "broadcast_match_created",
    "broadcast_match_updated",
    "broadcast_match_result",
    "broadcast_leaderboard_update",
    "broadcast_player_updated",
]
