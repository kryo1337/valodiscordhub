import discord
from discord.ext import commands, tasks
from discord import app_commands
from utils.db import get_leaderboard_page, get_total_pages, get_player_rank, update_leaderboard
from db.models.leaderboard import Leaderboard, LeaderboardEntry
import os
from dotenv import load_dotenv
from datetime import datetime, timezone

load_dotenv()
GUILD_ID = int(os.getenv("DISCORD_GUILD_ID", "0"))

class LeaderboardCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.leaderboard_channels = {}
        self.page_sizes = [10, 25, 50]
        self.current_page_sizes = {}
        self.last_update = None
        self.bot.add_listener(self.on_ready)

    async def update_leaderboard(self):
        try:
            guild = self.bot.get_guild(GUILD_ID)
            if not guild:
                return

            category = discord.utils.get(guild.categories, name="valohub")
            if not category:
                return

            channel = discord.utils.get(category.channels, name="leaderboard")
            if not channel:
                return

            self.last_update = datetime.now(timezone.utc)
            
            for channel_id, data in self.leaderboard_channels.items():
                channel = self.bot.get_channel(channel_id)
                if channel:
                    rank_group = data["rank_group"]
                    all_players = get_leaderboard_page(rank_group, 1, 1000)
                    sorted_players = sorted(all_players, key=lambda x: x.points, reverse=True)
                    
                    if sorted_players:
                        first_player = sorted_players[0]
                        await self.update_leaderboard_display(channel, str(first_player.discord_id))
                    break
        except Exception as e:
            print(f"Error in update_leaderboard: {e}")

    async def on_ready(self):
        await self.setup_existing_leaderboards()

    async def setup_existing_leaderboards(self):
        guild = self.bot.get_guild(GUILD_ID)
        if not guild:
            return

        category = discord.utils.get(guild.categories, name="valohub")
        if not category:
            return

        channel = discord.utils.get(category.channels, name="leaderboard")
        if channel:
            async for message in channel.history(limit=None):
                try:
                    await message.delete()
                except discord.NotFound:
                    pass
            
            self.leaderboard_channels[channel.id] = {
                "rank_group": "imm-radiant",
                "page": 1
            }
            self.current_page_sizes[channel.id] = 10
            
            rank_group = "imm-radiant"
            all_players = get_leaderboard_page(rank_group, 1, 1000)
            sorted_players = sorted(all_players, key=lambda x: x.points, reverse=True)
            
            if sorted_players:
                first_player = sorted_players[0]
                await self.update_leaderboard_display(channel, str(first_player.discord_id))

    @app_commands.command(name="setup_leaderboard")
    @app_commands.default_permissions(administrator=True)
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def setup_leaderboard(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        category = discord.utils.get(interaction.guild.categories, name="valohub")
        if category:
            for channel in category.channels:
                if channel.name == "leaderboard":
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
            name="leaderboard",
            overwrites=overwrites
        )

        self.leaderboard_channels[channel.id] = {
            "rank_group": "imm-radiant",
            "page": 1
        }
        self.current_page_sizes[channel.id] = 10

        await self.update_leaderboard_display(channel)
        await interaction.followup.send("✅ Leaderboard channel has been set up!", ephemeral=True)

    async def update_leaderboard_display(self, channel: discord.TextChannel, user_id: str = None):
        channel_id = channel.id
        if channel_id not in self.leaderboard_channels:
            return

        rank_group = self.leaderboard_channels[channel_id]["rank_group"]
        page = self.leaderboard_channels[channel_id]["page"]
        page_size = self.current_page_sizes[channel_id]

        await channel.purge()

        all_players = get_leaderboard_page(rank_group, 1, 1000)
        sorted_players = sorted(all_players, key=lambda x: x.points, reverse=True)
        
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        players = sorted_players[start_idx:end_idx]
        total_pages = (len(sorted_players) + page_size - 1) // page_size

        embed = discord.Embed(
            title=f"🏆 Leaderboard - {rank_group.upper()}",
            color=discord.Color.blue()
        )

        for i, player in enumerate(players, start=start_idx + 1):
            streak_text = f"🔥 {player.streak}" if player.streak >= 3 else ""
            try:
                discord_user = await channel.guild.fetch_member(int(player.discord_id))
                name = discord_user.display_name if discord_user else f"<@{player.discord_id}>"
            except:
                name = f"<@{player.discord_id}>"
            
            value = f"Rank: {player.rank} | Points: {player.points} | Winrate: {player.winrate}% | Matches: {player.matches_played} | {streak_text}"
            embed.add_field(name=f"{i}. {name}", value=value, inline=False)

        update_time = self.get_time_difference()
        embed.set_footer(text=f"Page {page}/{total_pages} | {page_size} players per page | Last update: {update_time}")

        view = LeaderboardView(self, channel, rank_group, page, total_pages, page_size)
        if user_id:
            view.last_user_id = user_id
        await channel.send(embed=embed, view=view)

    def get_time_difference(self):
        if not self.last_update:
            return "Never"
        
        now = datetime.now(timezone.utc)
        diff = now - self.last_update
        
        if diff.total_seconds() < 60:
            return "just now"
        elif diff.total_seconds() < 3600:
            minutes = int(diff.total_seconds() / 60)
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        else:
            hours = int(diff.total_seconds() / 3600)
            return f"{hours} hour{'s' if hours != 1 else ''} ago"

    @app_commands.command(name="test_leaderboard")
    @app_commands.default_permissions(administrator=True)
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def test_leaderboard(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        category = discord.utils.get(interaction.guild.categories, name="valohub")
        if not category:
            await interaction.followup.send(
                "❌ valohub category not found. Run /setup_leaderboard first.", ephemeral=True
            )
            return

        channel = discord.utils.get(category.channels, name="leaderboard")
        if not channel:
            await interaction.followup.send(
                "❌ Leaderboard channel not found. Run /setup_leaderboard first.", ephemeral=True
            )
            return

        rank_groups = ["iron-plat", "dia-asc", "imm-radiant"]
        for rank_group in rank_groups:
            test_players = []
            for i in range(15):
                discord_id = f"test_user_{rank_group}_{i}"
                points = 1000 - (i * 50)
                winrate = 60 - (i * 2)
                matches = 20 + (i * 5)
                streak = 3 if i < 3 else 0
                
                player = LeaderboardEntry(
                    discord_id=discord_id,
                    rank=f"Test Rank {i+1}",
                    points=points,
                    matches_played=matches,
                    winrate=winrate,
                    streak=streak
                )
                test_players.append(player)

            leaderboard = Leaderboard(rank_group=rank_group, players=test_players)
            update_leaderboard(rank_group, test_players)

        await self.update_leaderboard_display(channel)
        await interaction.followup.send(
            "✅ Added test data to all leaderboards!", ephemeral=True
        )

class LeaderboardView(discord.ui.View):
    def __init__(self, cog, channel, rank_group, current_page, total_pages, page_size):
        super().__init__(timeout=None)
        self.cog = cog
        self.channel = channel
        self.rank_group = rank_group
        self.current_page = current_page
        self.total_pages = total_pages
        self.page_size = page_size
        self.last_user_id = None

        self.add_item(RankGroupSelect(self))
        self.add_item(FirstPageButton(self))
        self.add_item(PreviousPageButton(self))
        self.add_item(NextPageButton(self))
        self.add_item(LastPageButton(self))
        self.add_item(PageSizeSelect(self))

    async def update_display(self, interaction: discord.Interaction = None):
        if interaction:
            self.last_user_id = str(interaction.user.id)
        await self.cog.update_leaderboard_display(self.channel, self.last_user_id)

class RankGroupSelect(discord.ui.Select):
    def __init__(self, view):
        options = [
            discord.SelectOption(
                label="Iron - Platinum",
                value="iron-plat",
                description="View Iron to Platinum leaderboard"
            ),
            discord.SelectOption(
                label="Diamond - Ascendant",
                value="dia-asc",
                description="View Diamond to Ascendant leaderboard"
            ),
            discord.SelectOption(
                label="Immortal - Radiant",
                value="imm-radiant",
                description="View Immortal to Radiant leaderboard"
            )
        ]
        super().__init__(
            placeholder="Select rank group",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        new_rank_group = self.values[0]
        self.view.rank_group = new_rank_group
        self.view.cog.leaderboard_channels[self.view.channel.id]["rank_group"] = new_rank_group
        self.view.current_page = 1
        await self.view.update_display(interaction)

class FirstPageButton(discord.ui.Button):
    def __init__(self, view):
        super().__init__(label="⏮️", style=discord.ButtonStyle.primary)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        self.view.current_page = 1
        await self.view.update_display(interaction)

class PreviousPageButton(discord.ui.Button):
    def __init__(self, view):
        super().__init__(label="◀️", style=discord.ButtonStyle.primary)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        if self.view.current_page > 1:
            self.view.current_page -= 1
            self.view.cog.leaderboard_channels[self.view.channel.id]["page"] = self.view.current_page
            await self.view.update_display(interaction)

class NextPageButton(discord.ui.Button):
    def __init__(self, view):
        super().__init__(label="▶️", style=discord.ButtonStyle.primary)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        if self.view.current_page < self.view.total_pages:
            self.view.current_page += 1
            self.view.cog.leaderboard_channels[self.view.channel.id]["page"] = self.view.current_page
            await self.view.update_display(interaction)

class LastPageButton(discord.ui.Button):
    def __init__(self, view):
        super().__init__(label="⏭️", style=discord.ButtonStyle.primary)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        self.view.current_page = self.view.total_pages
        self.view.cog.leaderboard_channels[self.view.channel.id]["page"] = self.view.current_page
        await self.view.update_display(interaction)

class PageSizeSelect(discord.ui.Select):
    def __init__(self, view):
        options = [
            discord.SelectOption(label=f"{size} players", value=str(size))
            for size in view.cog.page_sizes
        ]
        super().__init__(
            placeholder="Players per page",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        new_size = int(self.values[0])
        self.view.page_size = new_size
        self.view.cog.current_page_sizes[self.view.channel.id] = new_size
        self.view.current_page = 1
        await self.view.update_display(interaction)

async def setup(bot):
    await bot.add_cog(LeaderboardCog(bot)) 