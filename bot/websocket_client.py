"""
WebSocket client for bot to receive API events.

This module provides a WebSocket client that connects to the API server
and receives real-time events for queue updates, match changes, etc.
"""

import asyncio
import os
import json
import logging
from typing import Optional, Callable, Dict, Any
from pathlib import Path

import websockets
from websockets.exceptions import (
    ConnectionClosed,
    ConnectionClosedError,
    InvalidStatusCode,
)
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

logger = logging.getLogger("valohub")

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
BOT_API_TOKEN = os.getenv("BOT_API_TOKEN", "")

WS_URL = API_BASE_URL.replace("http://", "ws://").replace("https://", "wss://")


class WebSocketClient:
    """WebSocket client for bot to receive API events."""

    def __init__(self, bot=None):
        self.bot = bot
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.connected = False
        self.reconnect_delay = 1
        self.max_reconnect_delay = 60
        self.event_handlers: Dict[str, Callable] = {}
        self._running = False
        self._ping_task: Optional[asyncio.Task] = None
        self._connection_task: Optional[asyncio.Task] = None

    def on_event(self, event_type: str):
        """Decorator to register event handlers."""

        def decorator(handler: Callable):
            self.event_handlers[event_type] = handler
            return handler

        return decorator

    def register_handler(self, event_type: str, handler: Callable):
        """Register an event handler directly."""
        self.event_handlers[event_type] = handler
        logger.debug(f"Registered handler for event type: {event_type}")

    async def start(self):
        """Start the WebSocket client."""
        if self._running:
            logger.warning("WebSocket client already running")
            return

        self._running = True
        self._connection_task = asyncio.create_task(self._connection_loop())
        logger.info("WebSocket client started")

    async def stop(self):
        """Stop the WebSocket client."""
        self._running = False

        if self._ping_task:
            self._ping_task.cancel()
            try:
                await self._ping_task
            except asyncio.CancelledError:
                pass
            self._ping_task = None

        if self.ws:
            await self.ws.close()
            self.ws = None

        self.connected = False
        logger.info("WebSocket client stopped")

    async def _connection_loop(self):
        """Main connection loop with reconnection logic."""
        while self._running:
            try:
                await self._connect()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"WebSocket connection error: {e}")
                self.connected = False

                if self._running:
                    await self._reconnect()

    async def _connect(self):
        """Connect to WebSocket server."""
        ws_endpoint = f"{WS_URL}/ws/{BOT_API_TOKEN}"
        logger.info(f"Connecting to WebSocket: {WS_URL}/ws/***")

        try:
            self.ws = await websockets.connect(
                ws_endpoint,
                ping_interval=30,
                ping_timeout=10,
                close_timeout=5,
            )
            self.connected = True
            self.reconnect_delay = 1
            logger.info("WebSocket connected successfully")

            self._ping_task = asyncio.create_task(self._ping_loop())

            await self._receive_messages()

        except InvalidStatusCode as e:
            logger.error(f"WebSocket authentication failed: {e}")
            raise
        except ConnectionRefusedError:
            logger.error("WebSocket connection refused - is the API server running?")
            raise
        except Exception as e:
            logger.error(f"WebSocket connection failed: {e}")
            raise
        finally:
            self.connected = False

    async def _receive_messages(self):
        """Receive and dispatch events."""
        try:
            async for message in self.ws:
                if message == "pong":
                    continue

                try:
                    event = json.loads(message)
                    await self._dispatch_event(event)
                except json.JSONDecodeError:
                    logger.warning(f"Received non-JSON message: {message[:100]}")

        except ConnectionClosed as e:
            logger.warning(f"WebSocket connection closed: {e}")
        except ConnectionClosedError as e:
            logger.warning(f"WebSocket connection closed with error: {e}")
        except Exception as e:
            logger.error(f"Error receiving WebSocket messages: {e}")

    async def _dispatch_event(self, event: Dict[str, Any]):
        """Dispatch event to registered handler."""
        event_type = event.get("type")
        if not event_type:
            logger.warning(f"Received event without type: {event}")
            return

        handler = self.event_handlers.get(event_type)

        if handler:
            try:
                await handler(event)
                logger.debug(f"Handled event: {event_type}")
            except Exception as e:
                logger.error(f"Error handling {event_type}: {e}", exc_info=True)
        else:
            logger.debug(f"No handler registered for event type: {event_type}")

    async def _ping_loop(self):
        """Send ping every 30 seconds to keep connection alive."""
        try:
            while self.connected and self.ws:
                await asyncio.sleep(30)
                if self.ws and self.connected:
                    try:
                        await self.ws.send("ping")
                    except Exception as e:
                        logger.warning(f"Failed to send ping: {e}")
                        break
        except asyncio.CancelledError:
            pass

    async def _reconnect(self):
        """Wait with exponential backoff before reconnecting."""
        logger.info(f"Reconnecting in {self.reconnect_delay}s...")
        await asyncio.sleep(self.reconnect_delay)
        self.reconnect_delay = min(self.reconnect_delay * 2, self.max_reconnect_delay)

    @property
    def is_connected(self) -> bool:
        """Check if WebSocket is connected."""
        return self.connected and self.ws is not None


ws_client = WebSocketClient()
