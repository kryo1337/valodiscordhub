"""
WebSocket connection manager and endpoint for real-time updates.
"""

import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, status
from typing import Dict, Optional, Set
from datetime import datetime, timezone
from jose import JWTError, jwt
import json
import logging

from config import settings

logger = logging.getLogger("valohub")

MAX_WS_CONNECTIONS = 100

PING_INTERVAL_SECONDS = 30
PONG_TIMEOUT_SECONDS = 90  # 3 missed pings


class ConnectionManager:
    """Manages active WebSocket connections."""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.user_info: Dict[str, dict] = {}
        self.bot_connection: Optional[WebSocket] = None
        self.last_pong: Dict[str, datetime] = {}
        self.bot_last_pong: Optional[datetime] = None

    async def connect(self, websocket: WebSocket, user_info: dict) -> bool:
        """
        Accept and register a new connection.
        Returns True if connection was accepted, False if limit reached.
        """
        if len(self.active_connections) >= MAX_WS_CONNECTIONS:
            return False

        await websocket.accept()
        discord_id = user_info.get("discord_id", "")
        now = datetime.now(timezone.utc)

        # Handle bot connection specially
        if user_info.get("is_bot"):
            self.bot_connection = websocket
            self.bot_last_pong = now
            logger.info("WebSocket connected: Bot")
            return True

        self.active_connections[discord_id] = websocket
        self.user_info[discord_id] = user_info
        self.last_pong[discord_id] = now
        logger.info(f"WebSocket connected: {discord_id}")
        return True

    def disconnect(self, discord_id: str, is_bot: bool = False):
        """Remove a connection."""
        if is_bot:
            self.bot_connection = None
            self.bot_last_pong = None
            logger.info("WebSocket disconnected: Bot")
            return

        if discord_id in self.active_connections:
            del self.active_connections[discord_id]
        if discord_id in self.user_info:
            del self.user_info[discord_id]
        if discord_id in self.last_pong:
            del self.last_pong[discord_id]
        logger.info(f"WebSocket disconnected: {discord_id}")

    def update_pong(self, discord_id: str, is_bot: bool = False):
        """Update last pong time for heartbeat tracking."""
        now = datetime.now(timezone.utc)
        if is_bot:
            self.bot_last_pong = now
        else:
            self.last_pong[discord_id] = now

    def is_stale(self, discord_id: str, is_bot: bool = False) -> bool:
        """Check if connection is stale (no pong received within timeout)."""
        now = datetime.now(timezone.utc)
        if is_bot:
            if self.bot_last_pong is None:
                return True
            return (now - self.bot_last_pong).total_seconds() > PONG_TIMEOUT_SECONDS
        else:
            last = self.last_pong.get(discord_id)
            if last is None:
                return True
            return (now - last).total_seconds() > PONG_TIMEOUT_SECONDS

    async def send_personal(self, discord_id: str, event: dict):
        """Send event to a specific user."""
        websocket = self.active_connections.get(discord_id)
        if websocket:
            try:
                await websocket.send_text(json.dumps(event, default=str))
            except Exception as e:
                logger.error(f"Failed to send to {discord_id}: {e}")
                self.disconnect(discord_id)

    async def broadcast(self, event: dict, rank_group: Optional[str] = None):
        """
        Broadcast event to all connected users.
        If rank_group is provided, only send to users in that rank group.
        Also sends to bot connection if available.
        """
        event_json = json.dumps(event, default=str)
        disconnected_users: list[str] = []

        if self.bot_connection:
            try:
                await self.bot_connection.send_text(event_json)
            except Exception as e:
                logger.error(f"Failed to send to bot: {e}")
                self.bot_connection = None

        for discord_id, websocket in self.active_connections.items():
            # Filter by rank group if specified
            if rank_group:
                user_rank = self.user_info.get(discord_id, {}).get("rank", "")
                user_rg = self.get_rank_group_from_rank(user_rank)
                if user_rg != rank_group:
                    continue

            try:
                await websocket.send_text(event_json)
            except Exception as e:
                logger.error(f"Failed to send to {discord_id}: {e}")
                disconnected_users.append(discord_id)

        # Clean up disconnected users
        for discord_id in disconnected_users:
            self.disconnect(discord_id)

    @staticmethod
    def get_rank_group_from_rank(rank: str) -> Optional[str]:
        """Map rank to rank group."""
        if not rank:
            return None

        rank_lower = rank.lower()
        if rank_lower.startswith(("iron", "bronze", "silver", "gold", "platinum")):
            return "iron-plat"
        elif rank_lower.startswith(("diamond", "ascendant")):
            return "dia-asc"
        elif rank_lower.startswith(("immortal", "radiant")):
            return "imm-radiant"
        return None

    @property
    def connection_count(self) -> int:
        """Get total number of active connections."""
        count = len(self.active_connections)
        if self.bot_connection:
            count += 1
        return count


# Global connection manager
manager = ConnectionManager()

router = APIRouter(tags=["websocket"])


def validate_token(token: str) -> Optional[dict]:
    """
    Validate a JWT or Bot token and return user info.
    Returns None if validation fails.
    """
    # Check if it's the bot token
    if token == settings.bot_api_token:
        return {"discord_id": "bot", "username": "ValoHub Bot", "is_bot": True}

    # Try to decode as JWT
    try:
        payload = jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
        payload["is_bot"] = False
        return payload
    except JWTError:
        return None


@router.websocket("/ws/{token}")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str,
    rank_group: Optional[str] = Query(None),
):
    """
    WebSocket endpoint for real-time updates.

    Connect using: ws://host/ws/{jwt_token}?rank_group=iron-plat

    The token can be either a JWT token (for web users) or the bot API token.
    Optionally filter events by rank_group: iron-plat, dia-asc, imm-radiant

    Server sends "ping" every 30s. Client should respond with "pong".
    Connections with no pong in 90s are considered stale and closed.
    """
    # Validate token
    user_info = validate_token(token)
    if not user_info:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        logger.warning("WebSocket auth failed: invalid token")
        return

    # Store rank group preference if provided
    if rank_group and not user_info.get("is_bot"):
        user_info["preferred_rank_group"] = rank_group

    # Try to connect
    connected = await manager.connect(websocket, user_info)
    if not connected:
        await websocket.close(code=status.WS_1013_TRY_AGAIN_LATER)
        logger.warning("WebSocket connection limit reached")
        return

    discord_id = user_info.get("discord_id", "")
    is_bot = user_info.get("is_bot", False)

    async def heartbeat_loop():
        """Send pings and check for stale connections."""
        try:
            while True:
                await asyncio.sleep(PING_INTERVAL_SECONDS)

                # Check if connection is stale
                if manager.is_stale(discord_id, is_bot):
                    logger.warning(f"Connection stale for {discord_id}, closing")
                    await websocket.close(code=status.WS_1000_NORMAL_CLOSURE)
                    return

                # Send ping
                try:
                    await websocket.send_text("ping")
                except Exception:
                    return  # Connection closed
        except asyncio.CancelledError:
            pass

    # Start heartbeat task
    heartbeat_task = asyncio.create_task(heartbeat_loop())

    try:
        # Keep connection alive, receive messages
        while True:
            data = await websocket.receive_text()

            # Handle client ping (client -> server)
            if data == "ping":
                await websocket.send_text("pong")

            # Handle client pong response (client responding to server ping)
            elif data == "pong":
                manager.update_pong(discord_id, is_bot)

    except WebSocketDisconnect:
        manager.disconnect(discord_id, is_bot)
    except Exception as e:
        logger.error(f"WebSocket error for {discord_id}: {e}")
        manager.disconnect(discord_id, is_bot)
    finally:
        heartbeat_task.cancel()
        try:
            await heartbeat_task
        except asyncio.CancelledError:
            pass


@router.get("/ws/status")
async def websocket_status():
    """Get WebSocket connection status."""
    return {
        "active_connections": manager.connection_count,
        "max_connections": MAX_WS_CONNECTIONS,
        "bot_connected": manager.bot_connection is not None,
    }
