import discord
from discord.ext import commands
from discord import app_commands
from utils.db import get_leaderboard_page, get_player, get_user_preferences, save_user_preferences
from models.preferences import UserPreferences
import os
from dotenv import load_dotenv

load_dotenv()
GUILD_ID = int(os.getenv("DISCORD_GUILD_ID"))

class UserLeaderboardView(discord.ui.View):
    def __init__(self, cog, interaction, user_prefs, total_pages):
        super().__init__(timeout=None)
        self.cog = cog
        self.interaction = interaction
        self.user_prefs = user_prefs
        self.total_pages = total_pages
        self.message = None

        self.add_item(RankGroupSelect(self))
        self.add_item(FirstPageButton(self))
        self.add_item(PreviousPageButton(self))
        self.add_item(NextPageButton(self))
        self.add_item(LastPageButton(self))
        self.add_item(PageSizeSelect(self))

    async def update_display(self, interaction: discord.Interaction = None):
        await save_user_preferences(self.user_prefs)
        await self.cog.update_user_leaderboard_display(interaction or self.interaction, self.user_prefs, self)

class RankGroupSelect(discord.ui.Select):
    def __init__(self, view):
        options = [
            discord.SelectOption(
                label="Iron - Platinum",
                value="iron-plat",
                description="View Iron to Platinum leaderboard",
            ),
            discord.SelectOption(
                label="Diamond - Ascendant",
                value="dia-asc",
                description="View Diamond to Ascendant leaderboard",
            ),
            discord.SelectOption(
                label="Immortal - Radiant",
                value="imm-radiant",
                description="View Immortal to Radiant leaderboard",
            )
        ]
        super().__init__(
            placeholder="Select rank group",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="rank_group"
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        self.view.user_prefs.rank_group = self.values[0]
        self.view.user_prefs.page = 1
        await self.view.update_display(interaction)

class FirstPageButton(discord.ui.Button):
    def __init__(self, view):
        super().__init__(
            label="First",
            emoji="⏮️",
            style=discord.ButtonStyle.secondary,
            custom_id="first_page"
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        self.view.user_prefs.page = 1
        await self.view.update_display(interaction)

class PreviousPageButton(discord.ui.Button):
    def __init__(self, view):
        super().__init__(
            label="Previous",
            emoji="◀️",
            style=discord.ButtonStyle.secondary,
            custom_id="prev_page"
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        if self.view.user_prefs.page > 1:
            self.view.user_prefs.page -= 1
        await self.view.update_display(interaction)

class NextPageButton(discord.ui.Button):
    def __init__(self, view):
        super().__init__(
            label="Next",
            emoji="▶️",
            style=discord.ButtonStyle.secondary,
            custom_id="next_page"
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        if self.view.user_prefs.page < self.view.total_pages:
            self.view.user_prefs.page += 1
        await self.view.update_display(interaction)

class LastPageButton(discord.ui.Button):
    def __init__(self, view):
        super().__init__(
            label="Last",
            emoji="⏭️",
            style=discord.ButtonStyle.secondary,
            custom_id="last_page"
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        self.view.user_prefs.page = self.view.total_pages
        await self.view.update_display(interaction)

class PageSizeSelect(discord.ui.Select):
    def __init__(self, view):
        options = [
            discord.SelectOption(
                label=f"{size} players",
                value=str(size),
                emoji="👥"
            )
            for size in view.cog.page_sizes
        ]
        super().__init__(
            placeholder="Players per page",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="page_size"
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        self.view.user_prefs.page_size = int(self.values[0])
        self.view.user_prefs.page = 1
        await self.view.update_display(interaction)

class ShowLeaderboardButton(discord.ui.Button):
    def __init__(self, cog):
        super().__init__(
            label="Show Leaderboard",
            style=discord.ButtonStyle.primary,
            emoji="📊",
            custom_id="show_leaderboard"
        )
        self.cog = cog

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        user_prefs = await get_user_preferences(str(interaction.user.id))
        if not user_prefs:
            user_prefs = UserPreferences(
                discord_id=str(interaction.user.id),
                rank_group="imm-radiant",
                page=1,
                page_size=10
            )
        
        view = UserLeaderboardView(self.cog, interaction, user_prefs, 1)
        await self.cog.update_user_leaderboard_display(interaction, user_prefs, view)

class LeaderboardCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.leaderboard_channels = {}
        self.page_sizes = [5, 10, 25, 50]
        self.bot.add_listener(self.on_ready)

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
            
            await self.update_leaderboard_display(channel)

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

        await self.update_leaderboard_display(channel)
        await interaction.followup.send("✅ Leaderboard channel has been set up!", ephemeral=True)

    @app_commands.command(name="leaderboard")
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def show_leaderboard(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        user_prefs = await get_user_preferences(str(interaction.user.id))
        if not user_prefs:
            user_prefs = UserPreferences(
                discord_id=str(interaction.user.id),
                rank_group="imm-radiant",
                page=1,
                page_size=10
            )
        
        view = UserLeaderboardView(self, interaction, user_prefs, 1)
        await self.update_user_leaderboard_display(interaction, user_prefs, view)

    async def update_leaderboard_display(self, channel: discord.TextChannel):
        channel_id = channel.id
        if channel_id not in self.leaderboard_channels:
            return

        await channel.purge()
        embed = discord.Embed(
            title="Valorant Leaderboard",
            description="Click the button below to view the leaderboard!",
            color=discord.Color.blue()
        )
        
        view = discord.ui.View(timeout=None)
        view.add_item(ShowLeaderboardButton(self))
        await channel.send(embed=embed, view=view)

    async def update_user_leaderboard_display(self, interaction: discord.Interaction, user_prefs: UserPreferences, view: UserLeaderboardView = None):
        rank_group = user_prefs.rank_group
        page = user_prefs.page
        page_size = user_prefs.page_size

        all_players = await get_leaderboard_page(rank_group, 1, 1000)
        sorted_players = sorted(all_players, key=lambda x: x.points, reverse=True)
        
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        players = sorted_players[start_idx:end_idx]
        total_pages = max(1, (len(sorted_players) + page_size - 1) // page_size)
        
        if page > total_pages:
            user_prefs.page = total_pages
            page = total_pages
        elif page < 1:
            user_prefs.page = 1
            page = 1

        rank_group_colors = {
            "iron-plat": discord.Color.blue(),
            "dia-asc": discord.Color.green(),
            "imm-radiant": discord.Color.red()
        }
        
        embed = discord.Embed(
            title=f"🏆 Leaderboard - {rank_group.upper()}",
            color=rank_group_colors[rank_group]
        )

        for i, player in enumerate(players, start=start_idx + 1):
            streak_text = f"🔥 {player.streak}" if player.streak >= 3 else ""
            try:
                discord_user = await interaction.guild.fetch_member(int(player.discord_id))
                name = discord_user.display_name if discord_user else f"<@{player.discord_id}>"
            except:
                name = f"<@{player.discord_id}>"
            
            db_player = await get_player(player.discord_id)
            if not db_player:
                continue
            
            value = (
                f"• Rank: {db_player.rank}\n"
                f"• Points: {player.points}\n"
                f"• Winrate: {player.winrate}%\n"
                f"• Matches: {player.matches_played}\n"
                f"{streak_text}"
            )
            embed.add_field(name=f"#{i} {name}", value=value, inline=False)

        embed.set_footer(text=f"📄 Page {page}/{total_pages} | 👥 {page_size} players per page")

        if view:
            view.total_pages = total_pages
            
        if view and view.message:
            await view.message.edit(embed=embed, view=view)
        else:
            if view:
                view.message = await interaction.followup.send(embed=embed, view=view, ephemeral=True)
            else:
                view = UserLeaderboardView(self, interaction, user_prefs, total_pages)
                view.message = await interaction.followup.send(embed=embed, view=view, ephemeral=True)

async def setup(bot):
    await bot.add_cog(LeaderboardCog(bot)) 