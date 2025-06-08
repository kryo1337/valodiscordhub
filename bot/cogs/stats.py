import discord
from discord.ext import commands, tasks
from discord import app_commands
from utils.db import get_player_rank, get_leaderboard_page, get_player
import os
from dotenv import load_dotenv
from datetime import datetime, timezone
from typing import List

load_dotenv()
GUILD_ID = int(os.getenv("DISCORD_GUILD_ID", "0"))

class StatsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.stats_channels = {}
        self.last_update = None
        self.bot.add_listener(self.on_ready)

    async def on_ready(self):
        await self.setup_existing_stats_channels()

    async def setup_existing_stats_channels(self):
        guild = self.bot.get_guild(GUILD_ID)
        if not guild:
            return

        category = discord.utils.get(guild.categories, name="valohub")
        if not category:
            return

        channel = discord.utils.get(category.channels, name="stats")
        if channel:
            self.stats_channels[channel.id] = True
            await self.update_stats_display(channel)

    @app_commands.command(name="setup_stats")
    @app_commands.default_permissions(administrator=True)
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def setup_stats(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        category = discord.utils.get(interaction.guild.categories, name="valohub")
        if category:
            for channel in category.channels:
                if channel.name == "stats":
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
            name="stats",
            overwrites=overwrites
        )

        self.stats_channels[channel.id] = True
        await self.update_stats_display(channel)
        await interaction.followup.send("✅ Stats channel has been set up!", ephemeral=True)

    async def update_stats_display(self, channel: discord.TextChannel):
        await channel.purge()
        self.last_update = datetime.now(timezone.utc)

        guild = channel.guild
        all_players = []
        
        for rank_group in ["iron-plat", "dia-asc", "imm-radiant"]:
            players = get_leaderboard_page(rank_group, 1, 1000)
            all_players.extend(players)

        sorted_players = sorted(all_players, key=lambda x: x.points, reverse=True)
        
        has_players = False
        for player in sorted_players:
            try:
                discord_user = await guild.fetch_member(int(player.discord_id))
                if not discord_user:
                    continue

                rank_group = None
                for role in discord_user.roles:
                    if role.name in ["iron-plat", "dia-asc", "imm-radiant"]:
                        rank_group = role.name
                        break

                if not rank_group:
                    continue

                position = None
                for i, p in enumerate(sorted_players, start=1):
                    if p.discord_id == player.discord_id:
                        position = i
                        break

                db_player = get_player(player.discord_id)
                if not db_player:
                    continue

                embed = discord.Embed(
                    title=f"Player Statistics - {discord_user.display_name}",
                    color=discord.Color.dark_theme()
                )
                
                rank_group_display = {
                    "iron-plat": "Iron - Platinum",
                    "dia-asc": "Diamond - Ascendant",
                    "imm-radiant": "Immortal - Radiant"
                }
                
                streak_text = f"🔥 {player.streak}" if player.streak >= 3 else ""
                embed.add_field(
                    name="Rank Information",
                    value=(
                        f"• Rank: {db_player.rank}\n"
                        f"• Group: {rank_group_display[rank_group]}\n"
                        f"• Position: #{position}"
                    ),
                    inline=False
                )
                
                embed.add_field(
                    name="📊 Statistics",
                    value=(
                        f"• Points: {player.points}\n"
                        f"• Matches: {player.matches_played}\n"
                        f"• Wins: {int(player.matches_played * player.winrate / 100)}\n"
                        f"• Losses: {int(player.matches_played * (100 - player.winrate) / 100)}\n"
                        f"• Winrate: {player.winrate}%\n"
                        f"{streak_text}"
                    ),
                    inline=False
                )
                
                if position > 1:
                    points_to_next = sorted_players[position-2].points - player.points
                    embed.add_field(
                        name="📈 Progress",
                        value=f"Need {points_to_next} more points to reach position #{position-1}",
                        inline=False
                    )
                
                await channel.send(embed=embed)
                has_players = True
            except Exception as e:
                print(f"Error updating stats for player {player.discord_id}: {e}")

        if not has_players:
            embed = discord.Embed(
                title="No Stats Yet",
                description="Players who haven't played any matches will appear here once they start playing!",
                color=discord.Color.dark_theme()
            )
            await channel.send(embed=embed)

    @tasks.loop(minutes=5)
    async def update_stats_channels(self):
        for channel_id in self.stats_channels:
            channel = self.bot.get_channel(channel_id)
            if channel:
                await self.update_stats_display(channel)

    @update_stats_channels.before_loop
    async def before_update_stats_channels(self):
        await self.bot.wait_until_ready()

    @app_commands.command(name="stats", description="Display player statistics")
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def stats(
        self,
        interaction: discord.Interaction,
        user: discord.Member
    ):
        await interaction.response.defer()
        
        target_id = str(user.id)
        db_player = get_player(target_id)
        if not db_player:
            await interaction.followup.send(f"{user.mention} is not registered!", ephemeral=True)
            return

        rank_group = None
        for role in user.roles:
            if role.name in ["iron-plat", "dia-asc", "imm-radiant"]:
                rank_group = role.name
                break

        if not rank_group:
            await interaction.followup.send(f"{user.mention} doesn't have a valid rank group role!", ephemeral=True)
            return

        player = get_player_rank(rank_group, target_id)
        if not player:
            await interaction.followup.send(f"{user.mention} hasn't played any matches yet!", ephemeral=True)
            return

        all_players = get_leaderboard_page(rank_group, 1, 1000)
        sorted_players = sorted(all_players, key=lambda x: x.points, reverse=True)
        
        position = None
        for i, p in enumerate(sorted_players, start=1):
            if p.discord_id == player.discord_id:
                position = i
                break

        embed = discord.Embed(
            title=f"Player Statistics - {user.display_name}",
            color=discord.Color.dark_theme()
        )
        
        rank_group_display = {
            "iron-plat": "Iron - Platinum",
            "dia-asc": "Diamond - Ascendant",
            "imm-radiant": "Immortal - Radiant"
        }
        
        streak_text = f"🔥 {player.streak}" if player.streak >= 3 else ""
        embed.add_field(
            name="Rank Information",
            value=(
                f"• Rank: {db_player.rank}\n"
                f"• Group: {rank_group_display[rank_group]}\n"
                f"• Position: #{position}"
            ),
            inline=False
        )
        
        embed.add_field(
            name="📊 Statistics",
            value=(
                f"• Points: {player.points}\n"
                f"• Matches: {player.matches_played}\n"
                f"• Wins: {int(player.matches_played * player.winrate / 100)}\n"
                f"• Losses: {int(player.matches_played * (100 - player.winrate) / 100)}\n"
                f"• Winrate: {player.winrate}%\n"
                f"{streak_text}"
            ),
            inline=False
        )
        
        if position > 1:
            points_to_next = sorted_players[position-2].points - player.points
            embed.add_field(
                name="📈 Progress",
                value=f"Need {points_to_next} more points to reach position #{position-1}",
                inline=False
            )
        
        await interaction.followup.send(embed=embed)

    async def update_player_stats(self, channel: discord.TextChannel, player_ids: List[str]):
        guild = channel.guild
        all_players = []
        
        for rank_group in ["iron-plat", "dia-asc", "imm-radiant"]:
            players = get_leaderboard_page(rank_group, 1, 1000)
            all_players.extend(players)

        sorted_players = sorted(all_players, key=lambda x: x.points, reverse=True)
        
        messages = []
        async for msg in channel.history(limit=200):
            messages.append(msg)
            
        player_messages = {}
        
        for msg in messages:
            if not msg.embeds:
                continue
            embed = msg.embeds[0]
            if not embed.title or not embed.title.startswith("Player Statistics - "):
                continue
            player_name = embed.title.replace("Player Statistics - ", "")
            player_messages[player_name] = msg
        
        for player in sorted_players:
            if player.discord_id not in player_ids:
                continue
                
            try:
                discord_user = await guild.fetch_member(int(player.discord_id))
                if not discord_user:
                    continue

                db_player = get_player(player.discord_id)
                if not db_player:
                    continue

                rank_group = None
                for role in discord_user.roles:
                    if role.name in ["iron-plat", "dia-asc", "imm-radiant"]:
                        rank_group = role.name
                        break

                if not rank_group:
                    continue

                position = None
                for i, p in enumerate(sorted_players, start=1):
                    if p.discord_id == player.discord_id:
                        position = i
                        break

                embed = discord.Embed(
                    title=f"Player Statistics - {discord_user.display_name}",
                    color=discord.Color.dark_theme()
                )
                
                rank_group_display = {
                    "iron-plat": "Iron - Platinum",
                    "dia-asc": "Diamond - Ascendant",
                    "imm-radiant": "Immortal - Radiant"
                }
                
                streak_text = f"🔥 {player.streak}" if player.streak >= 3 else ""
                embed.add_field(
                    name="Rank Information",
                    value=(
                        f"• Rank: {db_player.rank}\n"
                        f"• Group: {rank_group_display[rank_group]}\n"
                        f"• Position: #{position}"
                    ),
                    inline=False    
                )
                
                embed.add_field(
                    name="📊 Statistics",
                    value=(
                        f"• Points: {player.points}\n"
                        f"• Matches: {player.matches_played}\n"
                        f"• Wins: {int(player.matches_played * player.winrate / 100)}\n"
                        f"• Losses: {int(player.matches_played * (100 - player.winrate) / 100)}\n"
                        f"• Winrate: {player.winrate}%\n"
                        f"{streak_text}"
                    ),
                    inline=False    
                )
                
                if position > 1:
                    points_to_next = sorted_players[position-2].points - player.points
                    embed.add_field(
                        name="📈 Progress",
                        value=f"Need {points_to_next} more points to reach position #{position-1}",
                        inline=False
                    )
                
                if discord_user.display_name in player_messages:
                    await player_messages[discord_user.display_name].edit(embed=embed)
                else:
                    await channel.send(embed=embed)
            except Exception as e:
                print(f"Error updating stats for player {player.discord_id}: {e}")

async def setup(bot):
    await bot.add_cog(StatsCog(bot)) 