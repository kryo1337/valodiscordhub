import discord
from discord.ext import commands
from discord import app_commands
from typing import List
from datetime import datetime
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
from .match import create_match


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

        try:
            player = get_player(user_id)
        except Exception as e:
            await interaction.response.send_message(
                "An error occurred while checking your registration.", ephemeral=True
            )
            return

        if not player:
            await interaction.response.send_message(
                "You need to register first using `/rank` command!", ephemeral=True
            )
            return

        try:
            queue = get_queue(self.rank_group)
        except Exception as e:
            await interaction.response.send_message(
                "An error occurred while accessing the queue.", ephemeral=True
            )
            return

        player_in_queue = any(p.discord_id == user_id for p in queue.players)

        if player_in_queue:
            try:
                queue = remove_player_from_queue(self.rank_group, user_id)
                await interaction.response.send_message(
                    "You have left the queue!", ephemeral=True
                )
            except Exception as e:
                await interaction.response.send_message(
                    "An error occurred while leaving the queue.", ephemeral=True
                )
                return
        else:
            try:
                queue = add_to_queue(self.rank_group, user_id)
                await interaction.response.send_message(
                    "You have joined the queue!", ephemeral=True
                )
            except Exception as e:
                await interaction.response.send_message(
                    "An error occurred while joining the queue.", ephemeral=True
                )
                return

        self.last_interaction[user_id] = current_time

        player_in_queue = any(p.discord_id == user_id for p in queue.players)
        button.label = "Leave Queue" if player_in_queue else "Join Queue"
        button.style = (
            discord.ButtonStyle.danger if player_in_queue else discord.ButtonStyle.primary
        )

        await interaction.message.edit(
            content=f"**{self.rank_group.upper()} Queue**\n"
                    f"Click the button to join/leave the queue!\n"
                    f"Current players in queue: {len(queue.players)}\n"
                    f"Players: {', '.join([f'<@{p.discord_id}>' for p in queue.players])}",
            view=self,
        )

        if len(queue.players) >= 10:
            matched_players = queue.players[:10]
            await create_match(interaction.guild, self.rank_group, matched_players)
            for player in matched_players:
                queue = remove_player_from_queue(self.rank_group, player.discord_id)
            await interaction.message.edit(
                content=f"**{self.rank_group.upper()} Queue**\n"
                        f"Click the button to join/leave the queue!\n"
                        f"Current players in queue: {len(queue.players)}\n"
                        f"Players: {', '.join([f'<@{p.discord_id}>' for p in queue.players])}",
                view=self,
            )

class QueueCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

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

async def setup(bot):
    await bot.add_cog(QueueCog(bot))