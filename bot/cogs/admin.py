import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional, Literal
import os
import asyncio
from pathlib import Path
from dotenv import load_dotenv
from utils.db import (
    get_match,
    update_match_result,
    get_active_matches,
    get_leaderboard,
    update_leaderboard,
    get_player,
    add_admin_log,
    remove_admin_log,
    is_player_banned,
    is_player_timeout,
    get_queue,
    remove_player_from_queue,
    update_player_rank,
    get_banned_players,
    get_timeout_players,
)
from models.leaderboard import LeaderboardEntry
from .leaderboard import LeaderboardCog
from datetime import datetime, timezone
import logging

load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")
GUILD_ID = int(os.getenv("DISCORD_GUILD_ID"))
logger = logging.getLogger("valohub")


class AdminCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.admin_channel_id = None
        self.bot.add_listener(self.on_ready)

    async def on_ready(self):
        await self.setup_existing_admin_channel()

    async def setup_existing_admin_channel(self):
        guild = self.bot.get_guild(GUILD_ID)
        if not guild:
            return

        category = discord.utils.get(guild.categories, name="Staff")
        if not category:
            return

        channel = discord.utils.get(category.channels, name="admin-panel")
        if channel:
            self.admin_channel_id = channel.id

    async def match_id_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> list[app_commands.Choice[str]]:
        matches = await get_active_matches()
        return [
            app_commands.Choice(name=match.match_id, value=match.match_id)
            for match in matches
            if current.lower() in match.match_id.lower()
        ][:25]

    def get_rank_group(self, rank: str) -> str:
        rank = rank.lower()
        if rank in ["iron", "bronze", "silver", "gold", "platinum"]:
            return "iron-plat"
        elif rank in ["diamond", "ascendant"]:
            return "dia-asc"
        elif rank in ["immortal", "radiant"]:
            return "imm-radiant"
        return "imm-radiant"

    async def update_leaderboard_points(self, match_id: str, winner: str):
        match = await get_match(match_id)
        if not match or not match.players_red or not match.players_blue:
            logger.error(
                f"update_leaderboard_points: match not found or malformed for {match_id}"
            )
            return

        first_player = await get_player(match.players_red[0])
        if not first_player or not first_player.rank:
            return

        rank_group = self.get_rank_group(first_player.rank)

        leaderboard = await get_leaderboard(rank_group)
        current_entries = {str(p.discord_id): p for p in leaderboard.players}
        updated_entries = []

        all_match_players = match.players_red + match.players_blue
        player_ranks = {}
        for player_id in all_match_players:
            player = await get_player(player_id)
            if player and player.rank:
                player_ranks[player_id] = player.rank

        winning_team = match.players_red if winner == "red" else match.players_blue
        for player_id in winning_team:
            if player_id in current_entries:
                entry = current_entries[player_id]
                entry.points += 10
                entry.matches_played += 1
                entry.wins += 1
                entry.winrate = (entry.wins / entry.matches_played) * 100
                entry.streak = max(0, entry.streak) + 1
            else:
                entry = LeaderboardEntry(
                    discord_id=player_id,
                    rank=player_ranks.get(player_id, "Unranked"),
                    points=1010,
                    matches_played=1,
                    wins=1,
                    winrate=100.0,
                    streak=1,
                )
            updated_entries.append(entry)

        losing_team = match.players_blue if winner == "red" else match.players_red
        for player_id in losing_team:
            if player_id in current_entries:
                entry = current_entries[player_id]
                entry.points = max(0, entry.points - 10)
                entry.matches_played += 1
                entry.winrate = (entry.wins / entry.matches_played) * 100
                entry.streak = min(0, entry.streak) - 1
            else:
                entry = LeaderboardEntry(
                    discord_id=player_id,
                    rank=player_ranks.get(player_id, "Unranked"),
                    points=990,
                    matches_played=1,
                    wins=0,
                    winrate=0.0,
                    streak=-1,
                )
            updated_entries.append(entry)

        await update_leaderboard(rank_group, updated_entries)

        history_cog = self.bot.get_cog("HistoryCog")
        if history_cog:
            await history_cog.add_match_to_history(match)

        leaderboard_cog = self.bot.get_cog("LeaderboardCog")
        if leaderboard_cog:
            guild = self.bot.get_guild(GUILD_ID)
            if guild:
                category = discord.utils.get(guild.categories, name="Hub")
                if category:
                    channel = discord.utils.get(category.channels, name="leaderboard")
                    if channel:
                        await leaderboard_cog.update_leaderboard_display(channel)

    @app_commands.command(name="set_result")
    @app_commands.default_permissions(administrator=True)
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    @app_commands.describe(
        match_id="The ID of the match to update",
        result="The match result (red/blue/cancelled)",
        red_score="Red team's score (required if not cancelled)",
        blue_score="Blue team's score (required if not cancelled)",
    )
    async def set_result(
        self,
        interaction: discord.Interaction,
        match_id: str,
        result: Literal["red", "blue", "cancelled"] = "red",
        red_score: Optional[int] = None,
        blue_score: Optional[int] = None,
    ):
        await interaction.response.defer(ephemeral=True)

        match = await get_match(match_id)
        if not match:
            await interaction.followup.send("Match not found!", ephemeral=True)
            return
        if match.players_red is None or match.players_blue is None:
            await interaction.followup.send(
                "Match data incomplete; cannot set result.", ephemeral=True
            )
            return

        if result != "cancelled":
            if red_score is None or blue_score is None:
                await interaction.followup.send(
                    "Both red_score and blue_score are required when setting a match result!",
                    ephemeral=True,
                )
                return

            if not (0 <= red_score <= 13 and 0 <= blue_score <= 13):
                await interaction.followup.send(
                    "Invalid scores! Scores must be between 0 and 13.", ephemeral=True
                )
                return

        if result == "cancelled" and match.result and match.result != "cancelled":
            await self.revert_leaderboard_points(match_id, match.result)
            await add_admin_log(
                action="revert_match",
                admin_discord_id=str(interaction.user.id),
                match_id=match_id,
                reason="Match result reverted due to cancellation",
            )

        await update_match_result(
            match_id=match_id,
            red_score=red_score if result != "cancelled" else None,
            blue_score=blue_score if result != "cancelled" else None,
            result=result,
        )

        if result != "cancelled":
            await self.update_leaderboard_points(match_id, result)
            await add_admin_log(
                action="set_result",
                admin_discord_id=str(interaction.user.id),
                match_id=match_id,
                reason=f"Match result set to {result} (Red: {red_score}, Blue: {blue_score})",
            )
        else:
            await add_admin_log(
                action="cancel_match",
                admin_discord_id=str(interaction.user.id),
                match_id=match_id,
                reason="Match cancelled by admin",
            )

        await interaction.followup.send(
            f"✅ Match result updated!\n"
            f"Result: **{result.title()}**"
            + (
                f"\n🔴 Red Team: {red_score}\n🔵 Blue Team: {blue_score}"
                if result != "cancelled"
                else ""
            ),
            ephemeral=True,
        )

        await asyncio.sleep(5)
        await self.cleanup_match_channels(interaction.guild, match_id)

    async def revert_leaderboard_points(self, match_id: str, previous_result: str):
        match = await get_match(match_id)

        first_player = await get_player(match.players_red[0])
        if not first_player or not first_player.rank:
            return

        rank_group = self.get_rank_group(first_player.rank)

        leaderboard = await get_leaderboard(rank_group)
        current_entries = {str(p.discord_id): p for p in leaderboard.players}
        updated_entries = []

        all_match_players = match.players_red + match.players_blue
        player_ranks = {}
        for player_id in all_match_players:
            player = await get_player(player_id)
            if player and player.rank:
                player_ranks[player_id] = player.rank

        winning_team = (
            match.players_red if previous_result == "red" else match.players_blue
        )
        for player_id in winning_team:
            if player_id in current_entries:
                entry = current_entries[player_id]
                entry.points -= 10
                entry.matches_played -= 1
                entry.wins -= 1
                if entry.matches_played > 0:
                    entry.winrate = (entry.wins / entry.matches_played) * 100
                else:
                    entry.winrate = 0.0
                entry.streak = max(0, entry.streak - 1)
                updated_entries.append(entry)

        losing_team = (
            match.players_blue if previous_result == "red" else match.players_red
        )
        for player_id in losing_team:
            if player_id in current_entries:
                entry = current_entries[player_id]
                entry.points += 10
                entry.matches_played -= 1
                if entry.matches_played > 0:
                    entry.winrate = (entry.wins / entry.matches_played) * 100
                else:
                    entry.winrate = 0.0
                entry.streak = min(0, entry.streak + 1)
                updated_entries.append(entry)

        await update_leaderboard(rank_group, updated_entries)

        history_cog = self.bot.get_cog("HistoryCog")
        if history_cog:
            await history_cog.remove_match_from_history(match)

        leaderboard_cog = self.bot.get_cog("LeaderboardCog")
        if leaderboard_cog:
            guild = self.bot.get_guild(GUILD_ID)
            if guild:
                category = discord.utils.get(guild.categories, name="Hub")
                if category:
                    channel = discord.utils.get(category.channels, name="leaderboard")
                    if channel:
                        await leaderboard_cog.update_leaderboard_display(channel)

    async def cleanup_match_channels(self, guild: discord.Guild, match_id: str):
        try:
            match_category = discord.utils.get(guild.categories, name=match_id)
            if match_category:
                for channel in match_category.channels:
                    await channel.delete(reason="Match completed")

                await match_category.delete(reason="Match completed")
        except Exception as e:
            print(f"Error cleaning up match channels: {e}")

    @set_result.autocomplete("match_id")
    async def match_id_autocomplete_callback(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> list[app_commands.Choice[str]]:
        return await self.match_id_autocomplete(interaction, current)

    @app_commands.command(name="setup_admin")
    @app_commands.default_permissions(administrator=True)
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def setup_admin(
        self,
        interaction: discord.Interaction,
    ):
        await interaction.response.defer(ephemeral=True)

        category = discord.utils.get(interaction.guild.categories, name="Staff")
        if not category:
            category = await interaction.guild.create_category("Staff")

        existing_channel = discord.utils.get(category.channels, name="admin-panel")
        if existing_channel:
            await existing_channel.delete()

        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(
                read_messages=False
            ),
            interaction.guild.me: discord.PermissionOverwrite(
                read_messages=True, send_messages=True
            ),
        }

        try:
            channel = await category.create_text_channel(
                name="admin-panel",
                overwrites=overwrites,
                topic="Admin reports and notifications",
            )
            self.admin_channel_id = channel.id

            embed = discord.Embed(
                title="Admin Reports Channel",
                description="This channel is for admin reports and notifications.",
                color=discord.Color.dark_theme(),
            )
            await channel.send(embed=embed)

            existing_ranks_channel = discord.utils.get(
                category.channels, name="admin-ranks"
            )
            if existing_ranks_channel:
                await existing_ranks_channel.delete()

            ranks_overwrites = {
                interaction.guild.default_role: discord.PermissionOverwrite(
                    read_messages=False
                ),
                interaction.guild.me: discord.PermissionOverwrite(
                    read_messages=True, send_messages=True
                ),
            }

            ranks_channel = await category.create_text_channel(
                name="admin-ranks",
                overwrites=ranks_overwrites,
                topic="Rank verification requests",
            )

            embed_ranks = discord.Embed(
                title="Rank Verification Requests",
                description="Rank verification requests will appear here for admin review.",
                color=discord.Color.blue(),
            )
            await ranks_channel.send(embed=embed_ranks)

            await interaction.followup.send(
                f"✅ Admin channels created:\n"
                f"• Admin: {channel.mention}\n"
                f"• Admin-Ranks: {ranks_channel.mention}",
                ephemeral=True,
            )
        except Exception as e:
            await interaction.followup.send(
                f"❌ Failed to create admin channels: {str(e)}", ephemeral=True
            )

    async def send_admin_report(
        self, match_id: str, source_channel_id: int, embed: discord.Embed
    ):
        if not self.admin_channel_id:
            return None

        channel = self.bot.get_channel(self.admin_channel_id)
        if not channel:
            return None

        source_channel = self.bot.get_channel(source_channel_id)
        if source_channel:
            embed.add_field(
                name="📌 Match Channel", value=source_channel.mention, inline=False
            )

        view = AdminReportView()
        message = await channel.send(embed=embed, view=view)
        return message

    @app_commands.command(name="ban")
    @app_commands.default_permissions(administrator=True)
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    @app_commands.describe(user="The user to ban", reason="The reason for the ban")
    async def ban(
        self, interaction: discord.Interaction, user: discord.Member, reason: str
    ):
        await interaction.response.defer(ephemeral=True)

        if await is_player_banned(str(user.id)):
            await interaction.followup.send(
                f"❌ {user.mention} is already banned!", ephemeral=True
            )
            return

        await add_admin_log(
            "ban", str(interaction.user.id), str(user.id), reason=reason
        )
        logger.info(f"Banned user {user.id} for reason: {reason}")

        embed = discord.Embed(
            title="🔨 User Banned",
            description=f"{user.mention} has been banned",
            color=discord.Color.red(),
        )
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.add_field(name="Banned by", value=interaction.user.mention, inline=False)

        await interaction.followup.send("✅ User has been banned!", ephemeral=True)

        if self.admin_channel_id:
            channel = self.bot.get_channel(self.admin_channel_id)
            if channel:
                await channel.send(embed=embed)

        queue_cog = self.bot.get_cog("QueueCog")
        if queue_cog:
            rank_groups = ["iron-plat", "dia-asc", "imm-radiant"]
            for rank_group in rank_groups:
                try:
                    queue = await get_queue(rank_group)
                    if any(p.discord_id == str(user.id) for p in queue.players):
                        queue = await remove_player_from_queue(rank_group, str(user.id))
                    await queue_cog.update_queue_message(
                        interaction.guild, rank_group, queue
                    )
                except Exception as e:
                    logger.error(f"Error updating queue {rank_group}: {e}")
        else:
            logger.error("QueueCog not found")

    @app_commands.command(name="timeout")
    @app_commands.default_permissions(administrator=True)
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    @app_commands.describe(
        user="The user to timeout",
        reason="The reason for the timeout",
        duration="Duration in minutes",
    )
    async def timeout(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        reason: str,
        duration: int,
    ):
        await interaction.response.defer(ephemeral=True)

        if await is_player_banned(str(user.id)):
            await interaction.followup.send(
                f"❌ {user.mention} is currently banned. Please unban them first.",
                ephemeral=True,
            )
            return

        if await is_player_timeout(str(user.id)):
            await interaction.followup.send(
                f"❌ {user.mention} is already in timeout!", ephemeral=True
            )
            return

        await add_admin_log(
            "timeout",
            str(interaction.user.id),
            str(user.id),
            reason=reason,
            duration_minutes=duration,
        )
        logger.info(
            f"Timed out user {user.id} for {duration} minutes, reason: {reason}"
        )

        embed = discord.Embed(
            title="⏰ User Timed Out",
            description=f"{user.mention} has been timed out for {duration} minutes",
            color=discord.Color.orange(),
        )
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.add_field(name="Duration", value=f"{duration} minutes", inline=False)
        embed.add_field(
            name="Timed out by", value=interaction.user.mention, inline=False
        )

        await interaction.followup.send("✅ User has been timed out!", ephemeral=True)

        if self.admin_channel_id:
            channel = self.bot.get_channel(self.admin_channel_id)
            if channel:
                await channel.send(embed=embed)

        queue_cog = self.bot.get_cog("QueueCog")
        if queue_cog:
            rank_groups = ["iron-plat", "dia-asc", "imm-radiant"]
            for rank_group in rank_groups:
                try:
                    queue = await get_queue(rank_group)
                    if any(p.discord_id == str(user.id) for p in queue.players):
                        queue = await remove_player_from_queue(rank_group, str(user.id))
                    await queue_cog.update_queue_message(
                        interaction.guild, rank_group, queue
                    )
                except Exception as e:
                    logger.error(f"Error updating queue {rank_group}: {e}")
        else:
            logger.error("QueueCog not found")

    @app_commands.command(name="unban")
    @app_commands.default_permissions(administrator=True)
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    @app_commands.describe(user="The user to unban")
    async def unban(self, interaction: discord.Interaction, user: discord.Member):
        await interaction.response.defer(ephemeral=True)

        was_banned = await is_player_banned(str(user.id))
        was_timeout = await is_player_timeout(str(user.id))

        if not was_banned and not was_timeout:
            await interaction.followup.send(
                f"❌ {user.mention} is not banned or in timeout!", ephemeral=True
            )
            return

        if was_banned:
            await remove_admin_log("ban", str(user.id))
        if was_timeout:
            await remove_admin_log("timeout", str(user.id))

        embed = discord.Embed(
            title="✅ User Unbanned",
            description=f"{user.mention} has been unbanned",
            color=discord.Color.green(),
        )
        embed.add_field(
            name="Unbanned by", value=interaction.user.mention, inline=False
        )

        await interaction.followup.send("✅ User has been unbanned!", ephemeral=True)

        if self.admin_channel_id:
            channel = self.bot.get_channel(self.admin_channel_id)
            if channel:
                await channel.send(embed=embed)

    @app_commands.command(name="set_rank")
    @app_commands.default_permissions(administrator=True)
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def set_rank(
        self, interaction: discord.Interaction, user: discord.Member, rank: str
    ):
        await interaction.response.defer(ephemeral=True)

        try:
            rank_group = self.get_rank_group(rank)
            if not rank_group:
                await interaction.followup.send("Invalid rank!", ephemeral=True)
                return

            for role_name in ["iron-plat", "dia-asc", "imm-radiant"]:
                if role_name != rank_group:
                    role = discord.utils.get(interaction.guild.roles, name=role_name)
                    if role and role in user.roles:
                        await user.remove_roles(role)

            new_role = discord.utils.get(interaction.guild.roles, name=rank_group)
            if new_role and new_role not in user.roles:
                await user.add_roles(new_role)

            player = await get_player(str(user.id))
            if not player:
                await interaction.followup.send(
                    f"❌ {user.mention} is not registered!", ephemeral=True
                )
                return

            await update_player_rank(str(user.id), rank)

            leaderboard = await get_leaderboard(rank_group)
            if leaderboard:
                for entry in leaderboard.players:
                    if entry.discord_id == str(user.id):
                        entry.rank = rank
                        break
                await update_leaderboard(rank_group, leaderboard.players)

            leaderboard_cog = interaction.client.get_cog("LeaderboardCog")
            if leaderboard_cog:
                await leaderboard_cog.update_leaderboard()

            await add_admin_log(
                action="set_rank",
                admin_discord_id=str(interaction.user.id),
                target_discord_id=str(user.id),
                reason=f"Rank set to {rank}",
            )

            await interaction.followup.send(
                f"✅ Set {user.mention}'s rank to {rank}!", ephemeral=True
            )
        except Exception as e:
            print(f"Error in set_rank: {e}")
            await interaction.followup.send("❌ Failed to set rank!", ephemeral=True)

    @app_commands.command(name="set_points")
    @app_commands.default_permissions(administrator=True)
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    @app_commands.describe(
        user="The user to set points for", points="The new points value"
    )
    async def set_points(
        self, interaction: discord.Interaction, user: discord.Member, points: int
    ):
        await interaction.response.defer(ephemeral=True)

        try:
            player = await get_player(str(user.id))
            if not player:
                await interaction.followup.send(
                    f"❌ {user.mention} is not registered!", ephemeral=True
                )
                return

            await update_player_rank(str(user.id), player.rank)

            rank_group = self.get_rank_group(player.rank)
            leaderboard = await get_leaderboard(rank_group)
            for entry in leaderboard.players:
                if entry.discord_id == str(user.id):
                    entry.points = points
                    break
            await update_leaderboard(rank_group, leaderboard.players)

            await add_admin_log(
                action="set_points",
                admin_discord_id=str(interaction.user.id),
                target_discord_id=str(user.id),
                reason=f"Points set to {points}",
            )

            await interaction.followup.send(
                f"✅ {user.mention}'s points have been set to **{points}**",
                ephemeral=True,
            )
        except Exception as e:
            await interaction.followup.send(
                f"❌ An error occurred: {str(e)}", ephemeral=True
            )

    @app_commands.command(name="refresh_all")
    @app_commands.default_permissions(administrator=True)
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def refresh_all(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        try:
            queue_cog = self.bot.get_cog("QueueCog")
            leaderboard_cog = self.bot.get_cog("LeaderboardCog")
            rank_cog = self.bot.get_cog("Rank")
            history_cog = self.bot.get_cog("HistoryCog")
            stats_cog = self.bot.get_cog("StatsCog")

            if queue_cog:
                await queue_cog.setup_existing_queues()
                await interaction.followup.send(
                    "✅ Queue channels refreshed", ephemeral=True
                )

            if leaderboard_cog:
                await leaderboard_cog.setup_existing_leaderboards()
                await interaction.followup.send(
                    "✅ Leaderboard channel refreshed", ephemeral=True
                )

            if rank_cog:
                await rank_cog.setup_existing_rank_channel()
                await interaction.followup.send(
                    "✅ Rank channel refreshed", ephemeral=True
                )

            if history_cog:
                await history_cog.setup_existing_history_channels()
                await interaction.followup.send(
                    "✅ History channel refreshed", ephemeral=True
                )

            if stats_cog:
                await stats_cog.setup_existing_stats_channels()
                await interaction.followup.send(
                    "✅ Stats channel refreshed", ephemeral=True
                )

            await add_admin_log(
                action="refresh_all",
                admin_discord_id=str(interaction.user.id),
                reason="All channels refreshed",
            )

            await interaction.followup.send(
                "✅ All channels have been refreshed!", ephemeral=True
            )

        except Exception as e:
            await interaction.followup.send(
                f"❌ Failed to refresh channels: {str(e)}", ephemeral=True
            )

    @app_commands.command(name="setup_all")
    @app_commands.default_permissions(administrator=True)
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def setup_all(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        try:
            await interaction.followup.send(
                "🔧 Setting up admin channels...", ephemeral=True
            )
            await self.setup_admin.callback(self, interaction)

            queue_cog = self.bot.get_cog("QueueCog")
            if queue_cog:
                await interaction.followup.send(
                    "🔧 Setting up queue channels...", ephemeral=True
                )
                await queue_cog.setup_queue.callback(queue_cog, interaction)

            leaderboard_cog = self.bot.get_cog("LeaderboardCog")
            if leaderboard_cog:
                await interaction.followup.send(
                    "🔧 Setting up leaderboard channel...", ephemeral=True
                )
                await leaderboard_cog.setup_leaderboard.callback(
                    leaderboard_cog, interaction
                )

            rank_cog = self.bot.get_cog("Rank")
            if rank_cog:
                await interaction.followup.send(
                    "🔧 Setting up rank channel...", ephemeral=True
                )
                await rank_cog.setup_rank.callback(rank_cog, interaction)

            history_cog = self.bot.get_cog("HistoryCog")
            if history_cog:
                await interaction.followup.send(
                    "🔧 Setting up history channel...", ephemeral=True
                )
                await history_cog.setup_history.callback(history_cog, interaction)

            stats_cog = self.bot.get_cog("StatsCog")
            if stats_cog:
                await interaction.followup.send(
                    "🔧 Setting up stats channel...", ephemeral=True
                )
                await stats_cog.setup_stats.callback(stats_cog, interaction)

            await add_admin_log(
                action="setup_all",
                admin_discord_id=str(interaction.user.id),
                reason="All channels set up",
            )

            await interaction.followup.send(
                "✅ All channels have been set up successfully!\n"
                "Categories created:\n"
                "• **Staff**: admin, admin-ranks\n"
                "• **Hub**: queues, leaderboard, history, rank, stats\n"
                "• **Matches**: (will be created automatically when matches start)",
                ephemeral=True,
            )

        except Exception as e:
            await interaction.followup.send(
                f"❌ Failed to setup channels: {str(e)}", ephemeral=True
            )

    @app_commands.command(name="list_bans")
    @app_commands.default_permissions(administrator=True)
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def list_bans(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        banned_players = await get_banned_players()
        if not banned_players:
            await interaction.followup.send("No active bans found.", ephemeral=True)
            return

        embed = discord.Embed(title="🔨 Active Bans", color=discord.Color.red())

        for ban in banned_players:
            user = interaction.guild.get_member(int(ban["target_discord_id"]))
            if user:
                embed.add_field(
                    name=f"{user.display_name}",
                    value=f"Reason: {ban['reason']}\nBanned at: <t:{int(ban['timestamp'].timestamp())}:R>",
                    inline=False,
                )

        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="list_timeouts")
    @app_commands.default_permissions(administrator=True)
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def list_timeouts(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        timeout_players = await get_timeout_players()
        if not timeout_players:
            await interaction.followup.send("No active timeouts found.", ephemeral=True)
            return

        embed = discord.Embed(title="⏰ Active Timeouts", color=discord.Color.orange())

        current_time = datetime.now(timezone.utc)
        for timeout in timeout_players:
            timeout_time = timeout["timestamp"]
            if timeout_time.tzinfo is None:
                timeout_time = timeout_time.replace(tzinfo=timezone.utc)
            duration = timeout["duration_minutes"]
            time_diff = (current_time - timeout_time).total_seconds() / 60

            if time_diff < duration:
                user = interaction.guild.get_member(int(timeout["target_discord_id"]))
                if user:
                    remaining_time = int(duration - time_diff)
                    embed.add_field(
                        name=f"{user.display_name}",
                        value=f"Reason: {timeout['reason']}\nDuration: {timeout['duration_minutes']} minutes\nRemaining: {remaining_time} minutes\nTimed out at: <t:{int(timeout['timestamp'].timestamp())}:R>",
                        inline=False,
                    )

        if not embed.fields:
            await interaction.followup.send("No active timeouts found.", ephemeral=True)
            return

        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="rank_tickets")
    @app_commands.default_permissions(administrator=True)
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def rank_tickets(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        try:
            category = discord.utils.get(interaction.guild.categories, name="Staff")
            if not category:
                await interaction.followup.send(
                    "❌ Staff category not found!", ephemeral=True
                )
                return

            admin_ranks_channel = discord.utils.get(
                category.channels, name="admin-ranks"
            )
            if not admin_ranks_channel:
                await interaction.followup.send(
                    "❌ admin-ranks channel not found!", ephemeral=True
                )
                return

            ticket_messages = []
            async for message in admin_ranks_channel.history(limit=20):
                if (
                    message.author == interaction.client.user
                    and message.embeds
                    and message.embeds[0].footer
                    and "Ticket ID:" in message.embeds[0].footer.text
                ):
                    ticket_messages.append(message)

            if not ticket_messages:
                await interaction.followup.send(
                    "No active rank tickets found.", ephemeral=True
                )
                return

            embed = discord.Embed(
                title="🎮 Active Rank Tickets",
                description=f"Found {len(ticket_messages)} active rank verification requests",
                color=discord.Color.blue(),
            )

            for i, message in enumerate(ticket_messages[:10], 1):
                embed_data = message.embeds[0]
                user_id = embed_data.footer.text.split(": ")[1]
                user = interaction.guild.get_member(int(user_id))
                user_mention = user.mention if user else f"<@{user_id}>"

                riot_id = embed_data.description.split("**Riot ID:** ")[1].split("\n")[
                    0
                ]

                embed.add_field(
                    name=f"Ticket #{i}",
                    value=f"User: {user_mention}\nRiot ID: {riot_id}\n[View Ticket]({message.jump_url})",
                    inline=True,
                )

            if len(ticket_messages) > 10:
                embed.add_field(
                    name="More Tickets",
                    value=f"There are {len(ticket_messages) - 10} more tickets. Check the {admin_ranks_channel.mention} channel.",
                    inline=False,
                )

            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            await interaction.followup.send(f"❌ Error: {str(e)}", ephemeral=True)


class AdminReportView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Close Case",
        style=discord.ButtonStyle.danger,
        emoji="✅",
        custom_id="close_case",
    )
    async def close_case(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "You don't have permission to close cases!", ephemeral=True
            )
            return

        confirm_view = ConfirmCloseView(interaction.message)
        await interaction.response.send_message(
            "Are you sure you want to close this case?",
            view=confirm_view,
            ephemeral=True,
        )


class ConfirmCloseView(discord.ui.View):
    def __init__(self, message: discord.Message):
        super().__init__(timeout=60)
        self.message = message

    @discord.ui.button(
        label="Yes, close case",
        style=discord.ButtonStyle.danger,
        emoji="🔒",
        custom_id="confirm_close",
    )
    async def confirm(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "You don't have permission to close cases!", ephemeral=True
            )
            return

        await self.message.delete()
        await interaction.response.send_message("✅ Case closed!", ephemeral=True)
        self.stop()

    @discord.ui.button(
        label="Cancel",
        style=discord.ButtonStyle.secondary,
        emoji="❌",
        custom_id="cancel_close",
    )
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "❌ Case closure cancelled.", ephemeral=True
        )
        self.stop()

    async def on_timeout(self):
        try:
            await self.message.channel.send(
                "⏰ Case closure timed out.", ephemeral=True
            )
        except:
            pass


async def setup(bot):
    await bot.add_cog(AdminCog(bot))
