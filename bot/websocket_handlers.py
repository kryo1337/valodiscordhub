"""
WebSocket event handlers for the Discord bot.

This module registers handlers for all WebSocket events received from the API.
Handlers update Discord UI elements when actions occur via the frontend.
"""

import logging
import os
from pathlib import Path
from typing import Dict, Any

import discord
from dotenv import load_dotenv

from websocket_client import ws_client
from utils.db import get_queue
from models.queue import Queue

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

logger = logging.getLogger("valohub")

GUILD_ID = int(os.getenv("DISCORD_GUILD_ID", "0"))


def setup_handlers(bot: discord.ext.commands.Bot):
    """Register all WebSocket event handlers with access to the bot instance."""

    ws_client.bot = bot

    @ws_client.on_event("queue_update")
    async def handle_queue_update(event: Dict[str, Any]):
        """Handle queue update events from frontend/API."""
        # Skip events originating from bot to prevent loops
        if event.get("origin") == "bot":
            return

        action = event.get("action")
        rank_group = event.get("rank_group")
        discord_id = event.get("discord_id")
        players = event.get("players", [])
        queue_count = event.get("queue_count", 0)

        logger.info(
            f"WS: Queue update - {action} for {rank_group} (count: {queue_count})"
        )

        # Get the guild
        guild = bot.get_guild(GUILD_ID)
        if not guild:
            logger.warning(f"Could not find guild {GUILD_ID}")
            return

        # Get QueueCog and update the queue message
        queue_cog = bot.get_cog("QueueCog")
        if queue_cog and hasattr(queue_cog, "update_queue_message"):
            try:
                # Fetch fresh queue data from API
                queue = await get_queue(rank_group)
                if queue:
                    await queue_cog.update_queue_message(guild, rank_group, queue)
                    logger.info(f"Updated queue message for {rank_group}")
            except Exception as e:
                logger.error(f"Error updating queue message: {e}")
        else:
            logger.warning("QueueCog not found or missing update_queue_message method")

    @ws_client.on_event("match_created")
    async def handle_match_created(event: Dict[str, Any]):
        """Handle match created events from frontend/API."""
        # Skip events originating from bot to prevent loops
        if event.get("origin") == "bot":
            return

        match_id = event.get("match_id")
        rank_group = event.get("rank_group")
        players_red = event.get("players_red", [])
        players_blue = event.get("players_blue", [])
        captain_red = event.get("captain_red")
        captain_blue = event.get("captain_blue")

        logger.info(f"WS: Match created - {match_id} in {rank_group}")

        # Get the guild
        guild = bot.get_guild(GUILD_ID)
        if not guild:
            logger.warning(f"Could not find guild {GUILD_ID}")
            return

        # Get MatchCog and handle match creation
        match_cog = bot.get_cog("MatchCog")
        if match_cog and hasattr(match_cog, "on_match_created_from_api"):
            try:
                await match_cog.on_match_created_from_api(guild, event)
                logger.info(f"Handled match creation for {match_id}")
            except Exception as e:
                logger.error(f"Error handling match creation: {e}")
        else:
            logger.debug("MatchCog.on_match_created_from_api not implemented yet")

    @ws_client.on_event("match_updated")
    async def handle_match_updated(event: Dict[str, Any]):
        """Handle match updated events from frontend/API."""
        # Skip events originating from bot to prevent loops
        if event.get("origin") == "bot":
            return

        match_id = event.get("match_id")
        update_type = event.get("update_type")
        data = event.get("data", {})

        logger.info(f"WS: Match updated - {match_id} ({update_type})")

        # Get the guild
        guild = bot.get_guild(GUILD_ID)
        if not guild:
            logger.warning(f"Could not find guild {GUILD_ID}")
            return

        # Get MatchCog and handle match update
        match_cog = bot.get_cog("MatchCog")
        if match_cog and hasattr(match_cog, "on_match_updated_from_api"):
            try:
                await match_cog.on_match_updated_from_api(guild, event)
                logger.info(f"Handled match update for {match_id}")
            except Exception as e:
                logger.error(f"Error handling match update: {e}")
        else:
            logger.debug("MatchCog.on_match_updated_from_api not implemented yet")

    @ws_client.on_event("match_result")
    async def handle_match_result(event: Dict[str, Any]):
        """Handle match result events from frontend/API."""
        # Skip events originating from bot to prevent loops
        if event.get("origin") == "bot":
            return

        match_id = event.get("match_id")
        result = event.get("result")
        red_score = event.get("red_score")
        blue_score = event.get("blue_score")

        logger.info(
            f"WS: Match result - {match_id}: {result} (Red {red_score} - Blue {blue_score})"
        )

        # Get the guild
        guild = bot.get_guild(GUILD_ID)
        if not guild:
            logger.warning(f"Could not find guild {GUILD_ID}")
            return

        # Get MatchCog and handle match result
        match_cog = bot.get_cog("MatchCog")
        if match_cog and hasattr(match_cog, "on_match_result_from_api"):
            try:
                await match_cog.on_match_result_from_api(guild, event)
                logger.info(f"Handled match result for {match_id}")
            except Exception as e:
                logger.error(f"Error handling match result: {e}")
        else:
            logger.debug("MatchCog.on_match_result_from_api not implemented yet")

    @ws_client.on_event("leaderboard_update")
    async def handle_leaderboard_update(event: Dict[str, Any]):
        """Handle leaderboard update events from frontend/API."""
        # Skip events originating from bot to prevent loops
        if event.get("origin") == "bot":
            return

        rank_group = event.get("rank_group")
        top_players = event.get("top_players", [])

        logger.info(f"WS: Leaderboard updated for {rank_group}")

        # Get the guild
        guild = bot.get_guild(GUILD_ID)
        if not guild:
            logger.warning(f"Could not find guild {GUILD_ID}")
            return

        # Get LeaderboardCog and refresh display
        leaderboard_cog = bot.get_cog("LeaderboardCog")
        if leaderboard_cog and hasattr(
            leaderboard_cog, "on_leaderboard_update_from_api"
        ):
            try:
                await leaderboard_cog.on_leaderboard_update_from_api(guild, event)
                logger.info(f"Handled leaderboard update for {rank_group}")
            except Exception as e:
                logger.error(f"Error handling leaderboard update: {e}")
        else:
            logger.debug(
                "LeaderboardCog.on_leaderboard_update_from_api not implemented yet"
            )

    @ws_client.on_event("player_updated")
    async def handle_player_updated(event: Dict[str, Any]):
        """Handle player updated events from frontend/API."""
        # Skip events originating from bot to prevent loops
        if event.get("origin") == "bot":
            return

        discord_id = event.get("discord_id")
        field = event.get("field")
        value = event.get("value")

        logger.info(f"WS: Player updated - {discord_id}: {field} = {value}")

    logger.info("WebSocket event handlers registered")
