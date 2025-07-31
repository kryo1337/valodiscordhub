import discord
from discord.ext import commands
from discord import app_commands
from utils.db import get_player_rank, get_leaderboard_page, get_player
import os
from dotenv import load_dotenv

load_dotenv()
GUILD_ID = int(os.getenv("DISCORD_GUILD_ID"))

class StatsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.stats_channels = {}
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
            existing_channel = discord.utils.get(category.channels, name="stats")
            if existing_channel:
                await existing_channel.delete()
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

        for role_name in ["iron-plat", "dia-asc", "imm-radiant"]:
            role = discord.utils.get(interaction.guild.roles, name=role_name)
            if role:
                overwrites[role] = discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=False
                )

        channel = await category.create_text_channel(
            name="stats",
            overwrites=overwrites
        )

        self.stats_channels[channel.id] = True
        await self.update_stats_display(channel)
        await interaction.followup.send("✅ Stats channel has been set up!", ephemeral=True)

    async def update_stats_display(self, channel: discord.TextChannel):
        await channel.purge()
        embed = discord.Embed(
            title="Player Statistics",
            description="Click a button below to view statistics!",
            color=discord.Color.dark_theme()
        )
        
        view = discord.ui.View(timeout=None)
        view.add_item(ShowMyStatsButton(self))
        view.add_item(SearchStatsButton(self))
        await channel.send(embed=embed, view=view)

class ShowMyStatsButton(discord.ui.Button):
    def __init__(self, cog):
        super().__init__(
            label="My Stats",
            style=discord.ButtonStyle.primary,
            emoji="📊",
            custom_id="show_my_stats"
        )
        self.cog = cog

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        target_user = interaction.user
        target_id = str(target_user.id)
        db_player = await get_player(target_id)
        if not db_player:
            await interaction.followup.send(f"{target_user.mention} is not registered!", ephemeral=True)
            return

        rank_group = None
        for role in target_user.roles:
            if role.name in ["iron-plat", "dia-asc", "imm-radiant"]:
                rank_group = role.name
                break

        if not rank_group:
            await interaction.followup.send(f"{target_user.mention} doesn't have a valid rank group role!", ephemeral=True)
            return

        player = await get_player_rank(rank_group, target_id)
        if not player:
            await interaction.followup.send(f"{target_user.mention} hasn't played any matches yet!", ephemeral=True)
            return

        all_players = await get_leaderboard_page(rank_group, 1, 1000)
        sorted_players = sorted(all_players, key=lambda x: x.points, reverse=True)
        
        position = None
        for i, p in enumerate(sorted_players, start=1):
            if p.discord_id == player.discord_id:
                position = i
                break

        embed = discord.Embed(
            title=f"Player Statistics - {target_user.display_name}",
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
                f"• Winrate: {player.winrate:.2f}%\n"
                f"{streak_text}"
            ),
            inline=False
        )
        
        await interaction.followup.send(embed=embed, ephemeral=True)

class SearchStatsButton(discord.ui.Button):
    def __init__(self, cog):
        super().__init__(
            label="Search Player",
            style=discord.ButtonStyle.secondary,
            emoji="🔍",
            custom_id="search_stats"
        )
        self.cog = cog

    async def callback(self, interaction: discord.Interaction):
        modal = SearchStatsModal(self.cog)
        await interaction.response.send_modal(modal)

class SearchStatsModal(discord.ui.Modal, title="Search Player Stats"):
    def __init__(self, cog):
        super().__init__()
        self.cog = cog
        self.username = discord.ui.TextInput(
            label="Discord Username",
            placeholder="Enter the player's Discord username",
            required=True,
            min_length=2,
            max_length=32
        )
        self.add_item(self.username)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        guild = interaction.guild
        found_user = None
        
        async for member in guild.fetch_members():
            if member.name.lower() == self.username.value.lower() or member.display_name.lower() == self.username.value.lower():
                found_user = member
                break
        
        if not found_user:
            await interaction.followup.send("❌ Player not found!", ephemeral=True)
            return

        target_id = str(found_user.id)
        db_player = await get_player(target_id)
        if not db_player:
            await interaction.followup.send(f"{found_user.mention} is not registered!", ephemeral=True)
            return

        rank_group = None
        for role in found_user.roles:
            if role.name in ["iron-plat", "dia-asc", "imm-radiant"]:
                rank_group = role.name
                break

        if not rank_group:
            await interaction.followup.send(f"{found_user.mention} doesn't have a valid rank group role!", ephemeral=True)
            return

        player = await get_player_rank(rank_group, target_id)
        if not player:
            await interaction.followup.send(f"{found_user.mention} hasn't played any matches yet!", ephemeral=True)
            return

        all_players = await get_leaderboard_page(rank_group, 1, 1000)
        sorted_players = sorted(all_players, key=lambda x: x.points, reverse=True)
        
        position = None
        for i, p in enumerate(sorted_players, start=1):
            if p.discord_id == player.discord_id:
                position = i
                break

        embed = discord.Embed(
            title=f"Player Statistics - {found_user.display_name}",
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
                f"• Winrate: {player.winrate:.2f}%\n"
                f"{streak_text}"
            ),
            inline=False
        )
        
        await interaction.followup.send(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(StatsCog(bot)) 