import discord
from discord.ext import commands
from discord import app_commands
from typing import List
from datetime import datetime
import logging
from dotenv import load_dotenv
import os
from db.models.queue import QueueEntry
from utils.db import (
    get_player,
    add_to_queue,
    get_queue,
    remove_player_from_queue,
    create_player,
    update_queue,
)
from .match import MatchCog

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()
GUILD_ID = int(os.getenv("DISCORD_GUILD_ID", "0"))

class QueueView(discord.ui.View):
    def __init__(self, rank_group: str):
        super().__init__(timeout=None)
        self.rank_group = rank_group
        self.last_interaction = {}

    @discord.ui.button(
        label="Join Queue", style=discord.ButtonStyle.primary, custom_id="join_button"
    )
    async def join_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        current_time = datetime.now()
        user_id = str(interaction.user.id)
        
        if user_id in self.last_interaction:
            time_diff = (current_time - self.last_interaction[user_id]).total_seconds()
            if time_diff < 5:
                remaining_time = round(5 - time_diff)
                await interaction.response.send_message(
                    f"Please wait {remaining_time} seconds before joining/leaving the queue again!",
                    ephemeral=True
                )
                return

        player = get_player(str(interaction.user.id))

        if not player:
            await interaction.response.send_message(
                "You need to register first using `/rank` command!", ephemeral=True
            )
            return

        queue = get_queue(self.rank_group)
        player_in_queue = any(
            p.discord_id == str(interaction.user.id) for p in queue.players
        )

        if player_in_queue:
            queue = remove_player_from_queue(self.rank_group, str(interaction.user.id))
            await interaction.response.send_message(
                "You have left the queue!", ephemeral=True
            )
        else:
            queue = add_to_queue(self.rank_group, str(interaction.user.id))
            await interaction.response.send_message(
                "You have joined the queue!", ephemeral=True
            )

        self.last_interaction[user_id] = current_time

        player_in_queue = any(
            p.discord_id == str(interaction.user.id) for p in queue.players
        )
        button.label = "Leave Queue" if player_in_queue else "Join Queue"
        button.style = (
            discord.ButtonStyle.danger
            if player_in_queue
            else discord.ButtonStyle.primary
        )

        await interaction.message.edit(
            content=f"**{self.rank_group.upper()} Queue**\n"
            f"Click the button to join/leave the queue!\n"
            f"Current players in queue: {len(queue.players)}\n"
            f"Players: {', '.join([f'<@{p.discord_id}>' for p in queue.players])}",
            view=self,
        )

        if len(queue.players) >= 10:
            cog = interaction.client.get_cog("QueueCog")
            if cog:
                await cog.create_match(interaction.guild, self.rank_group, queue.players[:10])


class QueueCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.match_cog = None

    async def cog_load(self):
        self.match_cog = self.bot.get_cog("MatchCog")

    @app_commands.command(name="test_queue")
    @app_commands.default_permissions(administrator=True)
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def test_queue(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        category = discord.utils.get(interaction.guild.categories, name="Queue")
        if not category:
            await interaction.followup.send(
                "❌ Queue category not found. Run /setup_queue first.", ephemeral=True
            )
            return

        channel = discord.utils.get(category.channels, name="queue-imm-radiant")
        if not channel:
            await interaction.followup.send(
                "❌ Queue channel not found. Run /setup_queue first.", ephemeral=True
            )
            return

        test_players = []
        for i in range(9):
            discord_id = f"test_user_{i}"
            riot_id = f"TestUser{i}"
            rank = "Immortal 3"

            player = get_player(discord_id)
            if not player:
                player = create_player(discord_id, riot_id, rank)

            queue_entry = QueueEntry(
                discord_id=player.discord_id,
                riot_id=player.riot_id,
                rank=player.rank,
                join_time=datetime.now(),
            )
            test_players.append(queue_entry)

        queue = get_queue("imm-radiant")
        if not queue:
            queue = QueueEntry(rank_group="imm-radiant", players=[])

        queue.players.extend(test_players)
        update_queue("imm-radiant", queue.players)

        async for message in channel.history(limit=1):
            await message.edit(
                content=f"**IMMORTAL-RADIANT Queue**\n"
                f"Click the button to join/leave the queue!\n"
                f"Current players in queue: {len(queue.players)}\n"
                f"Players: {', '.join(f'<@{p.discord_id}>' for p in queue.players)}",
                view=QueueView("imm-radiant"),
            )
            break

        await interaction.followup.send(
            "✅ Added 9 test players to the queue!", ephemeral=True
        )

    @app_commands.command(name="setup_queue")
    @app_commands.default_permissions(administrator=True)
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def setup_queue(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        category = discord.utils.get(interaction.guild.categories, name="Queue")
        if category:
            for channel in category.channels:
                if channel.name.startswith("queue-"):
                    await channel.delete()
        else:
            category = await interaction.guild.create_category("Queue")
        
        rank_groups = ["iron-plat", "dia-asc", "imm-radiant"]
        for rank_group in rank_groups:
            overwrites = {
                interaction.guild.default_role: discord.PermissionOverwrite(
                    view_channel=False
                ),
                interaction.guild.me: discord.PermissionOverwrite(
                    view_channel=True, send_messages=True, manage_channels=True
                ),
            }

            role = discord.utils.get(interaction.guild.roles, name=rank_group)
            if role:
                overwrites[role] = discord.PermissionOverwrite(
                    view_channel=True, send_messages=True
                )

            channel = await category.create_text_channel(
                name=f"queue-{rank_group}", overwrites=overwrites
            )

            view = QueueView(rank_group)
            
            await channel.send(
                f"**{rank_group.upper()} Queue**\n"
                f"Click the button to join/leave the queue!\n"
                f"Current players in queue: 0",
                view=view,
            )

        await interaction.followup.send(
            "✅ Queue channels have been set up!", ephemeral=True
        )

    async def create_match(self, guild: discord.Guild, rank_group: str, players: List[QueueEntry]):
        queue = get_queue(rank_group)
        if not queue or len(queue.players) < 10:
            return

        queue.players = queue.players[10:]
        update_queue(rank_group, queue.players)

        category = discord.utils.get(guild.categories, name="Queue")
        queue_channel = discord.utils.get(category.channels, name=f"queue-{rank_group}")
        if queue_channel:
            async for message in queue_channel.history(limit=1):
                await message.edit(
                    content=f"**{rank_group.upper()} Queue**\n"
                    f"Click the button to join/leave the queue!\n"
                    f"Current players in queue: {len(queue.players)}\n"
                    f"Players: {', '.join(f'<@{p.discord_id}>' for p in queue.players)}",
                    view=QueueView(rank_group),
                )
                break

        if self.match_cog:
            await self.match_cog.create_match(guild, rank_group, players)


async def setup(bot):
    await bot.add_cog(QueueCog(bot)) 
