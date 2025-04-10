import discord
from discord.ext import commands
from discord import app_commands
from typing import List
from datetime import datetime, timezone
from utils.db import get_match_history
from db.models.match import Match
import os
from dotenv import load_dotenv

load_dotenv()
GUILD_ID = int(os.getenv("DISCORD_GUILD_ID", "0"))

class HistoryCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.history_channels = {}
        self.bot.add_listener(self.on_ready)

    async def on_ready(self):
        await self.setup_existing_history_channels()

    async def setup_existing_history_channels(self):
        guild = self.bot.get_guild(GUILD_ID)
        if not guild:
            return

        category = discord.utils.get(guild.categories, name="valohub")
        if not category:
            return

        channel = discord.utils.get(category.channels, name="history")
        if channel:
            self.history_channels[channel.id] = True

    @app_commands.command(name="setup_history")
    @app_commands.default_permissions(administrator=True)
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def setup_history(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        category = discord.utils.get(interaction.guild.categories, name="valohub")
        if category:
            for channel in category.channels:
                if channel.name == "history":
                    await channel.delete()
        else:
            category = await interaction.guild.create_category("valohub")

        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=False
            ),
            interaction.guild.me: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                manage_channels=True
            ),
        }

        channel = await category.create_text_channel(
            name="history",
            overwrites=overwrites
        )

        self.history_channels[channel.id] = True
        await self.update_history_display(channel)
        await interaction.followup.send("✅ History channel has been set up!", ephemeral=True)

    async def update_history_display(self, channel: discord.TextChannel):
        await channel.purge()

        matches = get_match_history(limit=None)
        if not matches:
            await channel.send("No match history found.")
            return

        for match in matches:
            red_team = [f"<@{id}>" for id in match.players_red]
            blue_team = [f"<@{id}>" for id in match.players_blue]
            
            red_team[0] = f"{red_team[0]} 👑"
            blue_team[0] = f"{blue_team[0]} 👑"
            
            red_team_str = f"**{', '.join(red_team)}**" if match.result == "red" else f"{', '.join(red_team)}"
            blue_team_str = f"**{', '.join(blue_team)}**" if match.result == "blue" else f"{', '.join(blue_team)}"
            
            duration = match.duration
            if duration:
                hours, remainder = divmod(duration.seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                duration_str = f"{hours}h {minutes}m {seconds}s"
            else:
                duration_str = "N/A"
            
            embed = discord.Embed(
                title=f"Match {match.match_id}",
                color=discord.Color.blue(),
                timestamp=match.created_at
            )
            
            embed.add_field(
                name="Teams",
                value=(
                    f"🔴 {red_team_str}\n"
                    f"🔵 {blue_team_str}"
                ),
                inline=False
            )
            
            embed.add_field(
                name="Result",
                value=f"Score: {match.red_score}-{match.blue_score}",
                inline=True
            )
            
            embed.add_field(
                name="Duration",
                value=duration_str,
                inline=True
            )

            await channel.send(embed=embed)

    async def add_new_match(self, match: Match):
        for channel_id in self.history_channels:
            channel = self.bot.get_channel(channel_id)
            if not channel:
                continue

            red_team = [f"<@{id}>" for id in match.players_red]
            blue_team = [f"<@{id}>" for id in match.players_blue]
            
            red_team[0] = f"👑 {red_team[0]}"
            blue_team[0] = f"👑 {blue_team[0]}"
            
            red_team_str = f"**{', '.join(red_team)}**" if match.result == "red" else f"{', '.join(red_team)}"
            blue_team_str = f"**{', '.join(blue_team)}**" if match.result == "blue" else f"{', '.join(blue_team)}"
            
            duration = match.duration
            if duration:
                hours, remainder = divmod(duration.seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                duration_str = f"{hours}h {minutes}m {seconds}s"
            else:
                duration_str = "N/A"
            
            embed = discord.Embed(
                title=f"Match {match.match_id}",
                color=discord.Color.blue(),
                timestamp=match.created_at
            )
            
            embed.add_field(
                name="Teams",
                value=(
                    f"🔴 {red_team_str}\n"
                    f"🔵 {blue_team_str}"
                ),
                inline=False
            )
            
            embed.add_field(
                name="Result",
                value=f"Score: {match.red_score}-{match.blue_score}",
                inline=True
            )
            
            embed.add_field(
                name="Duration",
                value=duration_str,
                inline=True
            )

            await channel.send(embed=embed)

    @commands.command(name="history")
    async def history(self, ctx, limit: int = 10):
        matches = await get_match_history(limit)
        
        if not matches:
            await ctx.send("No match history found.")
            return

        embed = discord.Embed(
            title="Match History",
            color=discord.Color.blue()
        )

        for match in matches:
            red_team = [f"<@{id}>" for id in match.players_red]
            blue_team = [f"<@{id}>" for id in match.players_blue]
            
            red_team[0] = f"👑 {red_team[0]}"
            blue_team[0] = f"👑 {blue_team[0]}"
            
            red_team_str = f"**{', '.join(red_team)}**" if match.result == "red" else f"{', '.join(red_team)}"
            blue_team_str = f"**{', '.join(blue_team)}**" if match.result == "blue" else f"{', '.join(blue_team)}"
            
            duration = match.duration
            if duration:
                hours, remainder = divmod(duration.seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                duration_str = f"{hours}h {minutes}m {seconds}s"
            else:
                duration_str = "N/A"
            
            embed.add_field(
                name=f"Match {match.match_id}",
                value=(
                    f"🔴 {red_team_str}\n"
                    f"🔵 {blue_team_str}\n"
                    f"Score: {match.red_score}-{match.blue_score}\n"
                    f"Created: {match.created_at.strftime('%Y-%m-%d %H:%M')}\n"
                    f"Duration: {duration_str}"
                ),
                inline=False
            )

        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(HistoryCog(bot)) 