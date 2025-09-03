import discord
from discord.ext import commands
from discord import app_commands
from typing import List
from datetime import datetime, timezone
from utils.db import get_match_history
from models.match import Match
import os
from dotenv import load_dotenv

load_dotenv()
GUILD_ID = int(os.getenv("DISCORD_GUILD_ID"))

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

        category = discord.utils.get(guild.categories, name="Hub")
        if not category:
            return

        channel = discord.utils.get(category.channels, name="history")
        if channel:
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(
                    view_channel=False,
                    send_messages=False
                ),
                guild.me: discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    manage_channels=True
                ),
            }

            for role_name in ["iron-plat", "dia-asc", "imm-radiant"]:
                role = discord.utils.get(guild.roles, name=role_name)
                if role:
                    overwrites[role] = discord.PermissionOverwrite(
                        view_channel=True,
                        send_messages=False
                    )

            await channel.edit(overwrites=overwrites)
            self.history_channels[channel.id] = True

    @app_commands.command(name="setup_history")
    @app_commands.default_permissions(administrator=True)
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def setup_history(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        category = discord.utils.get(interaction.guild.categories, name="Hub")
        if category:
            for channel in category.channels:
                if channel.name == "history":
                    await channel.delete()
        else:
            category = await interaction.guild.create_category("Hub")

        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(
                view_channel=False,
                send_messages=False
            ),
            interaction.guild.me: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                manage_channels=True
            ),
        }

        for role_name in ["iron-plat", "dia-asc", "imm-radiant"]:
            role = discord.utils.get(interaction.guild.roles, name=role_name)
            if role:
                overwrites[role] = discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=False
                )

        channel = await category.create_text_channel(
            name="history",
            overwrites=overwrites
        )

        self.history_channels[channel.id] = True
        await self.update_history_display(channel)
        await interaction.followup.send("✅ History channel has been set up!", ephemeral=True)

    async def update_history_display(self, channel: discord.TextChannel):
        await channel.purge()

        matches = await get_match_history(limit=None)
        if not matches:
            await channel.send("No match history found.")
            return

        for match in matches:
            if match.result == "cancelled":
                continue

            red_team = [f"<@{id}>" for id in match.players_red]
            blue_team = [f"<@{id}>" for id in match.players_blue]
            
            red_team[0] = f"{red_team[0]} 👑"
            blue_team[0] = f"{blue_team[0]} 👑"
            
            duration = match.duration
            if duration:
                hours, remainder = divmod(duration.seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                duration_str = f"{hours}h {minutes}m {seconds}s"
            else:
                duration_str = "N/A"
            
            rank_group_display = {
                "iron-plat": "Iron - Platinum",
                "dia-asc": "Diamond - Ascendant",
                "imm-radiant": "Immortal - Radiant"
            }

            red_side = "⚔️ Attack" if match.defense_start == "blue" else "🛡️ Defense"
            blue_side = "⚔️ Attack" if match.defense_start == "red" else "🛡️ Defense"
            
            embed = discord.Embed(
                title=f"Match {match.match_id}",
                description=f"**Rank Group: {rank_group_display[match.rank_group]}**",
                color=discord.Color.dark_theme(),
                timestamp=match.created_at
            )
            
            embed.add_field(
                name=f"🔴 Red Team {red_side}",
                value=f"• Captain: <@{match.players_red[0]}>\n" + "\n".join([f"• <@{id}>" for id in match.players_red[1:]]),
                inline=True
            )
            embed.add_field(
                name=f"🔵 Blue Team {blue_side}",
                value=f"• Captain: <@{match.players_blue[0]}>\n" + "\n".join([f"• <@{id}>" for id in match.players_blue[1:]]),
                inline=True
            )
            
            embed.add_field(
                name="Match Details",
                value=(
                    f"🗺️ Map: {match.selected_map or 'Unknown'}\n"
                    f"Score: {match.red_score}-{match.blue_score}\n"
                    f"Winner: {'🔴 Red Team' if match.result == 'red' else '🔵 Blue Team'}\n"
                    f"Duration: {duration_str}\n"
                    f"Date: {match.created_at.strftime('%Y-%m-%d %H:%M')}"
                ),
                inline=False
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
            
            duration = match.duration
            if duration:
                hours, remainder = divmod(duration.seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                duration_str = f"{hours}h {minutes}m {seconds}s"
            else:
                duration_str = "N/A"
            
            rank_group_display = {
                "iron-plat": "Iron - Platinum",
                "dia-asc": "Diamond - Ascendant",
                "imm-radiant": "Immortal - Radiant"
            }

            red_side = "⚔️ Attack" if match.defense_start == "blue" else "🛡️ Defense"
            blue_side = "⚔️ Attack" if match.defense_start == "red" else "🛡️ Defense"
            
            embed = discord.Embed(
                title=f"Match {match.match_id}",
                description=f"**Rank Group: {rank_group_display[match.rank_group]}**",
                color=discord.Color.dark_theme(),
                timestamp=match.created_at
            )
            
            embed.add_field(
                name=f"🔴 Red Team {red_side}",
                value=f"• Captain: <@{match.players_red[0]}>\n" + "\n".join([f"• <@{id}>" for id in match.players_red[1:]]),
                inline=True
            )
            embed.add_field(
                name=f"🔵 Blue Team {blue_side}",
                value=f"• Captain: <@{match.players_blue[0]}>\n" + "\n".join([f"• <@{id}>" for id in match.players_blue[1:]]),
                inline=True
            )
            
            embed.add_field(
                name="Match Details",
                value=(
                    f"🗺️ Map: {match.selected_map or 'Unknown'}\n"
                    f"Score: {match.red_score}-{match.blue_score}\n"
                    f"Winner: {'🔴 Red Team' if match.result == 'red' else '🔵 Blue Team'}\n"
                    f"Duration: {duration_str}\n"
                    f"Date: {match.created_at.strftime('%Y-%m-%d %H:%M')}"
                ),
                inline=False
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
            color=discord.Color.dark_theme()
        )

        for match in matches:
            if match.result == "cancelled":
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
            
            rank_group_display = {
                "iron-plat": "Iron - Platinum",
                "dia-asc": "Diamond - Ascendant",
                "imm-radiant": "Immortal - Radiant"
            }

            red_side = "⚔️ Attack" if match.defense_start == "blue" else "🛡️ Defense"
            blue_side = "⚔️ Attack" if match.defense_start == "red" else "🛡️ Defense"
            
            embed.add_field(
                name=f"Match {match.match_id}",
                value=(
                    f"**Rank Group: {rank_group_display[match.rank_group]}**\n"
                    f"🔴 Red Team {red_side}\n{red_team_str}\n"
                    f"🔵 Blue Team {blue_side}\n{blue_team_str}\n"
                    f"Score: {match.red_score}-{match.blue_score}\n"
                    f"Created: {match.created_at.strftime('%Y-%m-%d %H:%M')}\n"
                    f"Duration: {duration_str}"
                ),
                inline=False
            )

        await ctx.send(embed=embed)

    async def add_match_to_history(self, match: Match):
        if match.result == "cancelled":
            return

        for channel_id in self.history_channels:
            channel = self.bot.get_channel(channel_id)
            if not channel:
                continue

            red_team = [f"<@{id}>" for id in match.players_red]
            blue_team = [f"<@{id}>" for id in match.players_blue]
            
            red_team[0] = f"{red_team[0]} 👑"
            blue_team[0] = f"{blue_team[0]} 👑"
            
            duration = match.duration
            if duration:
                hours, remainder = divmod(duration.seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                duration_str = f"{hours}h {minutes}m {seconds}s"
            else:
                duration_str = "N/A"
            
            rank_group_display = {
                "iron-plat": "Iron - Platinum",
                "dia-asc": "Diamond - Ascendant",
                "imm-radiant": "Immortal - Radiant"
            }

            red_side = "⚔️ Attack" if match.defense_start == "blue" else "🛡️ Defense"
            blue_side = "⚔️ Attack" if match.defense_start == "red" else "🛡️ Defense"
            
            embed = discord.Embed(
                title=f"Match {match.match_id}",
                description=f"**Rank Group: {rank_group_display[match.rank_group]}**",
                color=discord.Color.dark_theme(),
                timestamp=match.created_at
            )
            
            embed.add_field(
                name=f"🔴 Red Team {red_side}",
                value=f"• Captain: <@{match.players_red[0]}>\n" + "\n".join([f"• <@{id}>" for id in match.players_red[1:]]),
                inline=True
            )
            embed.add_field(
                name=f"🔵 Blue Team {blue_side}",
                value=f"• Captain: <@{match.players_blue[0]}>\n" + "\n".join([f"• <@{id}>" for id in match.players_blue[1:]]),
                inline=True
            )
            
            embed.add_field(
                name="Match Details",
                value=(
                    f"🗺️ Map: {match.selected_map or 'Unknown'}\n"
                    f"Score: {match.red_score}-{match.blue_score}\n"
                    f"Winner: {'🔴 Red Team' if match.result == 'red' else '🔵 Blue Team'}\n"
                    f"Duration: {duration_str}\n"
                    f"Date: {match.created_at.strftime('%Y-%m-%d %H:%M')}"
                ),
                inline=False
            )

            await channel.send(embed=embed)

    async def remove_match_from_history(self, match: Match):
        for channel_id in self.history_channels:
            channel = self.bot.get_channel(channel_id)
            if not channel:
                continue

            async for message in channel.history(limit=200):
                if not message.embeds:
                    continue
                embed = message.embeds[0]
                if embed.title and embed.title == f"Match {match.match_id}":
                    await message.delete()
                    break

async def setup(bot):
    await bot.add_cog(HistoryCog(bot)) 