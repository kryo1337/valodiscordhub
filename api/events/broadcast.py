"""
Broadcasting utility functions for WebSocket events.
These functions create typed events and broadcast them to connected clients.
"""

from typing import List, Literal, Optional
import logging

from websocket import manager
from events.types import (
    EventOrigin,
    QueueUpdateEvent,
    MatchCreatedEvent,
    MatchUpdatedEvent,
    MatchResultEvent,
    LeaderboardUpdateEvent,
    PlayerUpdatedEvent,
)

logger = logging.getLogger("valohub")


async def broadcast_queue_update(
    rank_group: str,
    action: str,
    discord_id: Optional[str] = None,
    players: Optional[List[str]] = None,
    queue_count: int = 0,
    origin: EventOrigin = "frontend",
    origin_id: Optional[str] = None,
) -> None:
    """
    Broadcast queue update event.

    Args:
        rank_group: The rank group of the queue (iron-plat, dia-asc, imm-radiant)
        action: The action that occurred (joined, left, cleared)
        discord_id: Discord ID of the player (if applicable)
        players: List of player discord IDs currently in queue
        queue_count: Current number of players in queue
        origin: Source that triggered this event (bot or frontend)
        origin_id: Discord ID of the user who triggered this event
    """
    event = QueueUpdateEvent(
        rank_group=rank_group,
        action=action,
        discord_id=discord_id,
        queue_count=queue_count,
        players=players or [],
        origin=origin,
        origin_id=origin_id,
    )
    await _broadcast_event(event.model_dump(), rank_group)


async def broadcast_match_created(
    match_id: str,
    rank_group: str,
    players_red: List[str],
    players_blue: List[str],
    captain_red: str,
    captain_blue: str,
    origin: EventOrigin = "frontend",
    origin_id: Optional[str] = None,
) -> None:
    """
    Broadcast match created event.

    Args:
        match_id: Unique match identifier
        rank_group: The rank group of the match
        players_red: Discord IDs of red team players
        players_blue: Discord IDs of blue team players
        captain_red: Discord ID of red team captain
        captain_blue: Discord ID of blue team captain
        origin: Source that triggered this event (bot or frontend)
        origin_id: Discord ID of the user who triggered this event
    """
    event = MatchCreatedEvent(
        match_id=match_id,
        rank_group=rank_group,
        players_red=players_red,
        players_blue=players_blue,
        captain_red=captain_red,
        captain_blue=captain_blue,
        origin=origin,
        origin_id=origin_id,
    )
    await _broadcast_event(event.model_dump(), rank_group)


async def broadcast_match_updated(
    match_id: str,
    update_type: str,
    data: dict,
    rank_group: Optional[str] = None,
    origin: EventOrigin = "frontend",
    origin_id: Optional[str] = None,
) -> None:
    """
    Broadcast match updated event.

    Args:
        match_id: Unique match identifier
        update_type: Type of update (teams, captains, draft, score, cancelled)
        data: Update data payload
        rank_group: Optional rank group to filter recipients
        origin: Source that triggered this event (bot or frontend)
        origin_id: Discord ID of the user who triggered this event
    """
    event = MatchUpdatedEvent(
        match_id=match_id,
        update_type=update_type,
        data=data,
        origin=origin,
        origin_id=origin_id,
    )
    await _broadcast_event(event.model_dump(), rank_group)


async def broadcast_match_result(
    match_id: str,
    result: str,
    red_score: Optional[int] = None,
    blue_score: Optional[int] = None,
    rank_group: Optional[str] = None,
    origin: EventOrigin = "frontend",
    origin_id: Optional[str] = None,
) -> None:
    """
    Broadcast match result event.

    Args:
        match_id: Unique match identifier
        result: Match result (red, blue, cancelled)
        red_score: Red team score
        blue_score: Blue team score
        rank_group: Optional rank group to filter recipients
        origin: Source that triggered this event (bot or frontend)
        origin_id: Discord ID of the user who triggered this event
    """
    event = MatchResultEvent(
        match_id=match_id,
        result=result,
        red_score=red_score,
        blue_score=blue_score,
        origin=origin,
        origin_id=origin_id,
    )
    await _broadcast_event(event.model_dump(), rank_group)


async def broadcast_leaderboard_update(
    rank_group: str,
    top_players: List[dict],
    origin: EventOrigin = "frontend",
    origin_id: Optional[str] = None,
) -> None:
    """
    Broadcast leaderboard update event.

    Args:
        rank_group: The rank group of the leaderboard
        top_players: List of top player data dictionaries
        origin: Source that triggered this event (bot or frontend)
        origin_id: Discord ID of the user who triggered this event
    """
    event = LeaderboardUpdateEvent(
        rank_group=rank_group,
        top_players=top_players,
        origin=origin,
        origin_id=origin_id,
    )
    await _broadcast_event(event.model_dump(), rank_group)


async def broadcast_player_updated(
    discord_id: str,
    field: str,
    value: str,
    origin: EventOrigin = "frontend",
    origin_id: Optional[str] = None,
) -> None:
    """
    Broadcast player updated event.

    Args:
        discord_id: Discord ID of the player
        field: Field that was updated (rank, points, riot_id)
        value: New value of the field
        origin: Source that triggered this event (bot or frontend)
        origin_id: Discord ID of the user who triggered this event
    """
    event = PlayerUpdatedEvent(
        discord_id=discord_id,
        field=field,
        value=value,
        origin=origin,
        origin_id=origin_id,
    )
    await _broadcast_event(event.model_dump())


async def _broadcast_event(event: dict, rank_group: Optional[str] = None) -> None:
    """
    Helper to broadcast event without blocking.
    Logs failures but doesn't raise.

    Args:
        event: Event dictionary to broadcast
        rank_group: Optional rank group to filter recipients
    """
    try:
        await manager.broadcast(event, rank_group)
        logger.debug(
            f"Broadcast event: {event.get('type')} (origin: {event.get('origin')})"
        )
    except Exception as e:
        logger.error(f"Failed to broadcast event: {e}")
