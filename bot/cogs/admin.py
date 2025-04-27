import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional, Literal
import os
import asyncio
from dotenv import load_dotenv
from utils.db import get_match, update_match_result, get_active_matches, get_leaderboard, update_leaderboard, get_player, add_admin_log, remove_admin_log, is_player_banned, is_player_timeout, get_queue, remove_player_from_queue
from db.models.leaderboard import LeaderboardEntry
from .leaderboard import LeaderboardCog

load_dotenv()
GUILD_ID = int(os.getenv("DISCORD_GUILD_ID", "0"))

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

        category = discord.utils.get(guild.categories, name="valohub")
        if not category:
            return

        channel = discord.utils.get(category.channels, name="admin")
        if channel:
            self.admin_channel_id = channel.id

    async def match_id_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> list[app_commands.Choice[str]]:
        matches = get_active_matches()
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
        match = get_match(match_id)
        
        first_player = get_player(match.players_red[0])
        if not first_player or not first_player.rank:
            return
            
        rank_group = self.get_rank_group(first_player.rank)

        leaderboard = get_leaderboard(rank_group)
        current_entries = {str(p.discord_id): p for p in leaderboard.players}
        updated_entries = []

        all_match_players = match.players_red + match.players_blue
        player_ranks = {}
        for player_id in all_match_players:
            player = get_player(player_id)
            if player and player.rank:
                player_ranks[player_id] = player.rank

        winning_team = match.players_red if winner == "red" else match.players_blue
        for player_id in winning_team:
            if player_id in current_entries:
                entry = current_entries[player_id]
                entry.points += 10
                entry.matches_played += 1
                entry.winrate = (entry.winrate * (entry.matches_played - 1) + 100) / entry.matches_played
                entry.streak = max(0, entry.streak) + 1
            else:
                entry = LeaderboardEntry(
                    discord_id=player_id,
                    rank=player_ranks.get(player_id, "Unranked"),
                    points=1010,
                    matches_played=1,
                    winrate=100.0,
                    streak=1
                )
            updated_entries.append(entry)

        losing_team = match.players_blue if winner == "red" else match.players_red
        for player_id in losing_team:
            if player_id in current_entries:
                entry = current_entries[player_id]
                entry.points = max(0, entry.points - 10) 
                entry.matches_played += 1
                entry.winrate = (entry.winrate * (entry.matches_played - 1)) / entry.matches_played
                entry.streak = min(0, entry.streak) - 1
            else:
                entry = LeaderboardEntry(
                    discord_id=player_id,
                    rank=player_ranks.get(player_id, "Unranked"),
                    points=990,
                    matches_played=1,
                    winrate=0.0,
                    streak=-1
                )
            updated_entries.append(entry)

        update_leaderboard(rank_group, updated_entries)

        stats_cog = self.bot.get_cog("StatsCog")
        if stats_cog:
            for channel_id in stats_cog.stats_channels:
                channel = self.bot.get_channel(channel_id)
                if channel:
                    await stats_cog.update_player_stats(channel, all_match_players)

        history_cog = self.bot.get_cog("HistoryCog")
        if history_cog:
            await history_cog.add_match_to_history(match)

        leaderboard_cog = self.bot.get_cog("LeaderboardCog")
        if leaderboard_cog:
            await leaderboard_cog.update_leaderboard()

    @app_commands.command(name="set_result")
    @app_commands.default_permissions(administrator=True)
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    @app_commands.describe(
        match_id="The ID of the match to update",
        result="The match result (red/blue/cancelled)",
        red_score="Red team's score (required if not cancelled)",
        blue_score="Blue team's score (required if not cancelled)"
    )
    async def set_result(
        self,
        interaction: discord.Interaction,
        match_id: str,
        result: Literal["red", "blue", "cancelled"] = "red",
        red_score: Optional[int] = None,
        blue_score: Optional[int] = None
    ):
        await interaction.response.defer(ephemeral=True)

        match = get_match(match_id)
        if not match:
            await interaction.followup.send("Match not found!", ephemeral=True)
            return

        if result != "cancelled":
            if red_score is None or blue_score is None:
                await interaction.followup.send("Both red_score and blue_score are required when setting a match result!", ephemeral=True)
                return
            
            if not (0 <= red_score <= 13 and 0 <= blue_score <= 13):
                await interaction.followup.send("Invalid scores! Scores must be between 0 and 13.", ephemeral=True)
                return

        if result == "cancelled" and match.result and match.result != "cancelled":
            await self.revert_leaderboard_points(match_id, match.result)
            add_admin_log(
                action="revert_match",
                admin_discord_id=str(interaction.user.id),
                match_id=match_id,
                reason="Match result reverted due to cancellation"
            )

        update_match_result(
            match_id=match_id,
            red_score=red_score if result != "cancelled" else None,
            blue_score=blue_score if result != "cancelled" else None,
            result=result
        )

        if result != "cancelled":
            await self.update_leaderboard_points(match_id, result)
            add_admin_log(
                action="set_result",
                admin_discord_id=str(interaction.user.id),
                match_id=match_id,
                reason=f"Match result set to {result} (Red: {red_score}, Blue: {blue_score})"
            )
        else:
            add_admin_log(
                action="cancel_match",
                admin_discord_id=str(interaction.user.id),
                match_id=match_id,
                reason="Match cancelled by admin"
            )

        await interaction.followup.send(
            f"✅ Match result updated!\n"
            f"Result: **{result.title()}**"
            + (f"\n🔴 Red Team: {red_score}\n🔵 Blue Team: {blue_score}" if result != "cancelled" else ""),
            ephemeral=True
        )
        
        await asyncio.sleep(5)
        await self.cleanup_match_channels(interaction.guild, match_id)

    async def revert_leaderboard_points(self, match_id: str, previous_result: str):
        match = get_match(match_id)
        
        first_player = get_player(match.players_red[0])
        if not first_player or not first_player.rank:
            return
            
        rank_group = self.get_rank_group(first_player.rank)

        leaderboard = get_leaderboard(rank_group)
        current_entries = {str(p.discord_id): p for p in leaderboard.players}
        updated_entries = []

        all_match_players = match.players_red + match.players_blue
        player_ranks = {}
        for player_id in all_match_players:
            player = get_player(player_id)
            if player and player.rank:
                player_ranks[player_id] = player.rank

        winning_team = match.players_red if previous_result == "red" else match.players_blue
        for player_id in winning_team:
            if player_id in current_entries:
                entry = current_entries[player_id]
                entry.points -= 10
                entry.matches_played -= 1
                if entry.matches_played > 0:
                    entry.winrate = (entry.winrate * (entry.matches_played + 1) - 100) / entry.matches_played
                else:
                    entry.winrate = 0.0
                entry.streak = max(0, entry.streak - 1)
                updated_entries.append(entry)

        losing_team = match.players_blue if previous_result == "red" else match.players_red
        for player_id in losing_team:
            if player_id in current_entries:
                entry = current_entries[player_id]
                entry.points += 10
                entry.matches_played -= 1
                if entry.matches_played > 0:
                    entry.winrate = (entry.winrate * (entry.matches_played + 1)) / entry.matches_played
                else:
                    entry.winrate = 0.0
                entry.streak = min(0, entry.streak + 1)
                updated_entries.append(entry)

        update_leaderboard(rank_group, updated_entries)

        stats_cog = self.bot.get_cog("StatsCog")
        if stats_cog:
            for channel_id in stats_cog.stats_channels:
                channel = self.bot.get_channel(channel_id)
                if channel:
                    await stats_cog.update_player_stats(channel, all_match_players)

        history_cog = self.bot.get_cog("HistoryCog")
        if history_cog:
            await history_cog.remove_match_from_history(match)

        leaderboard_cog = self.bot.get_cog("LeaderboardCog")
        if leaderboard_cog:
            await leaderboard_cog.update_leaderboard()

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

        category = discord.utils.get(interaction.guild.categories, name="valohub")
        if not category:
            category = await interaction.guild.create_category("valohub")

        existing_channel = discord.utils.get(category.channels, name="admin")
        if existing_channel:
            await existing_channel.delete()

        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }

        try:
            channel = await category.create_text_channel(
                name="admin",
                overwrites=overwrites,
                topic="Admin reports and notifications"
            )
            self.admin_channel_id = channel.id
            
            embed = discord.Embed(
                title="Admin Reports Channel",
                description="This channel is for admin reports and notifications.",
                color=discord.Color.dark_theme()
            )
            await channel.send(embed=embed)
            
            await interaction.followup.send(
                f"✅ Admin channel created: {channel.mention}",
                ephemeral=True
            )
        except Exception as e:
            await interaction.followup.send(
                f"❌ Failed to create admin channel: {str(e)}",
                ephemeral=True
            )

    async def send_admin_report(self, match_id: str, source_channel_id: int, embed: discord.Embed):
        if not self.admin_channel_id:
            return None
            
        channel = self.bot.get_channel(self.admin_channel_id)
        if not channel:
            return None
            
        source_channel = self.bot.get_channel(source_channel_id)
        if source_channel:
            embed.add_field(
                name="📌 Match Channel",
                value=source_channel.mention,
                inline=False
            )
            
        view = AdminReportView()
        return await channel.send(embed=embed, view=view)

    @app_commands.command(name="ban")
    @app_commands.default_permissions(administrator=True)
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    @app_commands.describe(
        user="The user to ban",
        reason="The reason for the ban"
    )
    async def ban(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        reason: str
    ):
        await interaction.response.defer(ephemeral=True)

        if is_player_banned(str(user.id)):
            await interaction.followup.send(f"❌ {user.mention} is already banned!", ephemeral=True)
            return

        add_admin_log("ban", str(interaction.user.id), str(user.id), reason=reason)
        
        embed = discord.Embed(
            title="🔨 User Banned",
            description=f"{user.mention} has been banned from the queue system.",
            color=discord.Color.red()
        )
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.add_field(name="Banned by", value=interaction.user.mention, inline=False)
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        
        rank_groups = ["iron-plat", "dia-asc", "imm-radiant"]
        for rank_group in rank_groups:
            try:
                queue = get_queue(rank_group)
                if queue and any(p.discord_id == str(user.id) for p in queue.players):
                    remove_player_from_queue(rank_group, str(user.id))
            except Exception as e:
                print(f"Error removing banned player from queue {rank_group}: {e}")

    @app_commands.command(name="timeout")
    @app_commands.default_permissions(administrator=True)
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    @app_commands.describe(
        user="The user to timeout",
        reason="The reason for the timeout",
        duration="Duration in minutes"
    )
    async def timeout(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        reason: str,
        duration: int
    ):
        await interaction.response.defer(ephemeral=True)

        if is_player_timeout(str(user.id)):
            await interaction.followup.send(f"❌ {user.mention} is already in timeout!", ephemeral=True)
            return

        add_admin_log("timeout", str(interaction.user.id), str(user.id), reason=reason, duration_minutes=duration)
        
        embed = discord.Embed(
            title="⏰ User Timed Out",
            description=f"{user.mention} has been timed out from the queue system for {duration} minutes.",
            color=discord.Color.orange()
        )
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.add_field(name="Duration", value=f"{duration} minutes", inline=False)
        embed.add_field(name="Timed out by", value=interaction.user.mention, inline=False)
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        
        rank_groups = ["iron-plat", "dia-asc", "imm-radiant"]
        for rank_group in rank_groups:
            try:
                queue = get_queue(rank_group)
                if queue and any(p.discord_id == str(user.id) for p in queue.players):
                    remove_player_from_queue(rank_group, str(user.id))
            except Exception as e:
                print(f"Error removing timed out player from queue {rank_group}: {e}")

    @app_commands.command(name="unban")
    @app_commands.default_permissions(administrator=True)
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    @app_commands.describe(
        user="The user to unban"
    )
    async def unban(
        self,
        interaction: discord.Interaction,
        user: discord.Member
    ):
        await interaction.response.defer(ephemeral=True)

        was_banned = is_player_banned(str(user.id))
        was_timeout = is_player_timeout(str(user.id))

        if not was_banned and not was_timeout:
            await interaction.followup.send(f"❌ {user.mention} is not banned or in timeout!", ephemeral=True)
            return

        if was_banned:
            remove_admin_log("ban", str(user.id))
        if was_timeout:
            remove_admin_log("timeout", str(user.id))
        
        embed = discord.Embed(
            title="✅ User Unbanned",
            description=f"{user.mention} has been unbanned from the queue system.",
            color=discord.Color.green()
        )
        embed.add_field(name="Unbanned by", value=interaction.user.mention, inline=False)
        
        await interaction.followup.send(embed=embed, ephemeral=True)

class AdminReportView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Close Case",
        style=discord.ButtonStyle.danger,
        emoji="✅",
        custom_id="close_case"
    )
    async def close_case(self, interaction: discord.Interaction, button: discord.ui.Button):
        confirm_view = ConfirmCloseView(interaction.message)
        await interaction.response.send_message("Are you sure you want to close this case?", view=confirm_view, ephemeral=True)

class ConfirmCloseView(discord.ui.View):
    def __init__(self, message: discord.Message):
        super().__init__(timeout=60)
        self.message = message

    @discord.ui.button(
        label="Yes, close case",
        style=discord.ButtonStyle.danger,
        emoji="🔒",
        custom_id="confirm_close"
    )
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.message.delete()
        await interaction.response.send_message("✅ Case closed!", ephemeral=True)
        self.stop()

    @discord.ui.button(
        label="Cancel",
        style=discord.ButtonStyle.secondary,
        emoji="❌",
        custom_id="cancel_close"
    )
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("❌ Case closure cancelled.", ephemeral=True)
        self.stop()

    async def on_timeout(self):
        try:
            await self.message.channel.send("⏰ Case closure timed out.", ephemeral=True)
        except:
            pass

async def setup(bot):
    await bot.add_cog(AdminCog(bot)) 