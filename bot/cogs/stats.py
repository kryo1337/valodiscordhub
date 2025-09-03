import discord
from discord.ext import commands
from discord import app_commands
from utils.db import get_player_rank, get_leaderboard_page, get_player, get_player_match_history
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

        category = discord.utils.get(guild.categories, name="Hub")
        if not category:
            return

        channel = discord.utils.get(category.channels, name="stats")
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

            self.stats_channels[channel.id] = True
            await self.update_stats_display(channel)

    @app_commands.command(name="setup_stats")
    @app_commands.default_permissions(administrator=True)
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def setup_stats(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        category = discord.utils.get(interaction.guild.categories, name="Hub")
        if category:
            existing_channel = discord.utils.get(category.channels, name="stats")
            if existing_channel:
                await existing_channel.delete()
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
        view.add_item(ShowHistoryButton(self))
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

class ShowHistoryButton(discord.ui.Button):
    def __init__(self, cog):
        super().__init__(
            label="Show History",
            style=discord.ButtonStyle.success,
            emoji="📜",
            custom_id="show_history"
        )
        self.cog = cog

    async def callback(self, interaction: discord.Interaction):
        modal = HistoryLimitModal()
        await interaction.response.send_modal(modal)


class HistoryLimitModal(discord.ui.Modal, title="Match History Limit"):
    def __init__(self):
        super().__init__()
        self.limit_input = discord.ui.TextInput(
            label="How many recent matches? (1-20)",
            placeholder="Enter a number between 1 and 20",
            required=True,
            min_length=1,
            max_length=2
        )
        self.add_item(self.limit_input)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        try:
            limit = int(str(self.limit_input.value).strip())
        except ValueError:
            await interaction.followup.send("❌ Please enter a valid number between 1 and 20.", ephemeral=True)
            return

        if limit < 1 or limit > 20:
            await interaction.followup.send("❌ Number must be between 1 and 20.", ephemeral=True)
            return

        target_user = interaction.user
        target_id = str(target_user.id)
        db_player = await get_player(target_id)
        if not db_player:
            await interaction.followup.send(f"{target_user.mention} is not registered!", ephemeral=True)
            return

        matches = await get_player_match_history(target_id, limit=limit)
        if not matches:
            await interaction.followup.send(f"{target_user.mention} hasn't played any matches yet!", ephemeral=True)
            return

        rank_group_display = {
            "iron-plat": "Iron - Platinum",
            "dia-asc": "Diamond - Ascendant",
            "imm-radiant": "Immortal - Radiant"
        }

        for match in matches:
            if match.result == "cancelled":
                continue

            duration = match.duration
            if duration:
                hours, remainder = divmod(duration.seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                duration_str = f"{hours}h {minutes}m {seconds}s"
            else:
                duration_str = "N/A"

            red_side = "⚔️ Attack" if match.defense_start == "blue" else "🛡️ Defense"
            blue_side = "⚔️ Attack" if match.defense_start == "red" else "🛡️ Defense"
            user_result = "✅ Won" if (
                (match.result == "red" and target_id in match.players_red) or
                (match.result == "blue" and target_id in match.players_blue)
            ) else "❌ Lost"

            embed = discord.Embed(
                title=f"Match {match.match_id}",
                description=f"Rank Group: {rank_group_display[match.rank_group]}",
                color=discord.Color.dark_theme(),
                timestamp=match.created_at
            )

            embed.add_field(
                name=f"🔴 Red Team {red_side}",
                value=(
                    f"• Captain: <@{match.players_red[0]}>\n" +
                    ("\n".join([f"• <@{pid}>" for pid in match.players_red[1:]]) if len(match.players_red) > 1 else "")
                ),
                inline=True
            )

            embed.add_field(
                name=f"🔵 Blue Team {blue_side}",
                value=(
                    f"• Captain: <@{match.players_blue[0]}>\n" +
                    ("\n".join([f"• <@{pid}>" for pid in match.players_blue[1:]]) if len(match.players_blue) > 1 else "")
                ),
                inline=True
            )

            embed.add_field(
                name="Match Details",
                value=(
                    f"🗺️ Map: {match.selected_map or 'Unknown'}\n"
                    f"Score: {match.red_score}-{match.blue_score}\n"
                    f"Result: {user_result}\n"
                    f"Duration: {duration_str}\n"
                    f"Date: {match.created_at.strftime('%Y-%m-%d %H:%M')}\n"
                ),
                inline=False
            )

            await interaction.followup.send(embed=embed, ephemeral=True)

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