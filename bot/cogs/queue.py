import discord
from discord.ext import commands
from discord import app_commands
from typing import List, Optional
from datetime import datetime
import asyncio
import random
from dotenv import load_dotenv
import os
from db.models.queue import QueueEntry
from utils.db import (
    get_player,
    add_to_queue,
    remove_from_queue,
    get_queue,
    remove_player_from_queue,
    create_player,
    update_queue,
)

load_dotenv()
GUILD_ID = int(os.getenv("DISCORD_GUILD_ID", "0"))


class QueueView(discord.ui.View):
    def __init__(self, rank_group: str):
        super().__init__(timeout=None)
        self.rank_group = rank_group

    @discord.ui.button(
        label="Join Queue", style=discord.ButtonStyle.primary, custom_id="join_button"
    )
    async def join_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
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
                await cog.create_match(interaction.guild, self.rank_group)


class TeamSelectionView(discord.ui.View):
    def __init__(self, match_id: str, players: List[QueueEntry], captains: List[str]):
        super().__init__(timeout=5)
        self.match_id = match_id
        self.players = players
        self.captains = captains
        self.current_captain_index = 0
        self.red_team: List[str] = [captains[0]]
        self.blue_team: List[str] = [captains[1]]
        self.selection_order = [1, 2, 3, 4, 5, 6, 7, 8]
        self.current_selection_index = 0
        self.selection_message = None
        self.selection_task = None

    async def on_timeout(self):
        if self.selection_message:
            available_players = [
                p
                for p in self.players
                if p.discord_id not in self.red_team + self.blue_team
            ]
            if available_players:
                selected_player = random.choice(available_players)
                if self.current_captain_index == 0:
                    self.red_team.append(selected_player.discord_id)
                else:
                    self.blue_team.append(selected_player.discord_id)

                self.current_selection_index += 1
                if self.current_selection_index >= len(self.selection_order):
                    await self.end_selection(self.selection_message)
                else:
                    self.current_captain_index = 1 - self.current_captain_index
                    await self.update_selection_message(self.selection_message)
                    self.selection_task = asyncio.create_task(self.start_timeout())

    async def start_timeout(self):
        await asyncio.sleep(5)
        await self.on_timeout()

    async def update_selection_message(self, message: discord.Message):
        self.selection_message = message
        current_captain = self.captains[self.current_captain_index]
        remaining_players = len(
            [
                p
                for p in self.players
                if p.discord_id not in self.red_team + self.blue_team
            ]
        )

        message_content = (
            f"**Team Selection in Progress**\n\n"
            f"🔴 Red Team Captain: <@{self.captains[0]}>\n"
            f"🔵 Blue Team Captain: <@{self.captains[1]}>\n\n"
            f"Current Captain's Turn: <@{current_captain}>\n"
            f"Selection: {self.current_selection_index + 1}/8\n"
            f"Players Remaining: {remaining_players}\n"
            f"Time remaining: 30 seconds\n\n"
            f"Red Team: {', '.join([f'<@{id}>' for id in self.red_team])}\n"
            f"Blue Team: {', '.join([f'<@{id}>' for id in self.blue_team])}\n\n"
            f"Available Players: {', '.join([f'<@{p.discord_id}>' for p in self.players if p.discord_id not in self.red_team + self.blue_team])}"
        )
        await message.edit(content=message_content)
        if self.selection_task:
            self.selection_task.cancel()
        self.selection_task = asyncio.create_task(self.start_timeout())

    async def select_callback(self, interaction: discord.Interaction, selected_id: str):
        if self.current_captain_index == 0:
            self.red_team.append(selected_id)
        else:
            self.blue_team.append(selected_id)

        self.current_selection_index += 1
        if self.current_selection_index >= len(self.selection_order):
            await self.end_selection(interaction)
        else:
            self.current_captain_index = 1 - self.current_captain_index
            if self.selection_message:
                await self.update_selection_message(self.selection_message)

    @discord.ui.button(label="Select Player", style=discord.ButtonStyle.primary)
    async def select_player(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if str(interaction.user.id) != self.captains[self.current_captain_index]:
            await interaction.response.send_message(
                "It's not your turn to select!", ephemeral=True
            )
            return

        available_players = [
            p
            for p in self.players
            if p.discord_id not in self.red_team + self.blue_team
        ]
        if not available_players:
            await interaction.response.send_message(
                "No players available to select!", ephemeral=True
            )
            return

        select_menu = discord.ui.Select(
            placeholder="Select a player",
            options=[
                discord.SelectOption(
                    label=f"Player {i+1}",
                    value=p.discord_id,
                    description=f"<@{p.discord_id}>",
                )
                for i, p in enumerate(available_players)
            ],
        )

        async def select_callback(interaction: discord.Interaction):
            selected_id = select_menu.values[0]
            await self.select_callback(interaction, selected_id)

        select_menu.callback = select_callback
        view = discord.ui.View()
        view.add_item(select_menu)

        await interaction.response.send_message(
            "Select a player:", view=view, ephemeral=True
        )

    async def end_selection(self, interaction: discord.Interaction):
        side_view = SideSelectionView(self.match_id, self.red_team, self.blue_team)

        if isinstance(interaction, discord.Message):
            await interaction.edit(
                content=(
                    f"**Team Selection Complete!**\n\n"
                    f"🔴 Red Team: {', '.join([f'<@{id}>' for id in self.red_team])}\n"
                    f"🔵 Blue Team: {', '.join([f'<@{id}>' for id in self.blue_team])}\n\n"
                    f"Red Team Captain (<@{self.captains[0]}>) please select your side:"
                ),
                view=side_view,
            )
        else:
            await interaction.message.edit(
                content=(
                    f"**Team Selection Complete!**\n\n"
                    f"🔴 Red Team: {', '.join([f'<@{id}>' for id in self.red_team])}\n"
                    f"🔵 Blue Team: {', '.join([f'<@{id}>' for id in self.blue_team])}\n\n"
                    f"Red Team Captain (<@{self.captains[0]}>) please select your side:"
                ),
                view=side_view,
            )


class SideSelectionView(discord.ui.View):
    def __init__(
        self,
        match_id: str,
        red_team: List[str],
        blue_team: List[str],
        red_vc: discord.VoiceChannel,
        blue_vc: discord.VoiceChannel,
    ):
        super().__init__(timeout=30)
        self.match_id = match_id
        self.red_team = red_team
        self.blue_team = blue_team
        self.red_vc = red_vc
        self.blue_vc = blue_vc
        self.red_side = None
        self.blue_side = None
        self.side_task = None

    async def on_timeout(self):
        if not self.red_side:
            self.red_side = random.choice(["attack", "defense"])
        if not self.blue_side:
            self.blue_side = "defense" if self.red_side == "attack" else "attack"

        if hasattr(self, "last_message"):
            await self.check_sides(self.last_message)

    async def start_timeout(self):
        await asyncio.sleep(30)
        await self.on_timeout()

    @discord.ui.button(label="Select Attack", style=discord.ButtonStyle.primary)
    async def select_attack(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if str(interaction.user.id) not in self.red_team + self.blue_team:
            await interaction.response.send_message(
                "Only team members can select sides!", ephemeral=True
            )
            return

        if str(interaction.user.id) in self.red_team:
            self.red_side = "attack"
        else:
            self.blue_side = "attack"

        self.last_message = interaction.message
        await self.check_sides(interaction)

    @discord.ui.button(label="Select Defense", style=discord.ButtonStyle.secondary)
    async def select_defense(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if str(interaction.user.id) not in self.red_team + self.blue_team:
            await interaction.response.send_message(
                "Only team members can select sides!", ephemeral=True
            )
            return

        if str(interaction.user.id) in self.red_team:
            self.red_side = "defense"
        else:
            self.blue_side = "defense"

        self.last_message = interaction.message
        await self.check_sides(interaction)

    async def check_sides(self, interaction: discord.Interaction):
        if self.red_side and self.blue_side:
            match_category = interaction.channel.category
            red_vc = await interaction.guild.create_voice_channel(
                name="Red Team", category=match_category
            )
            blue_vc = await interaction.guild.create_voice_channel(
                name="Blue Team", category=match_category
            )

            score_view = ScoreSubmissionView(
                self.match_id, self.red_team, self.blue_team
            )

            await interaction.message.edit(
                content=(
                    f"**Sides Selected!**\n\n"
                    f"Red Team: {', '.join([f'<@{id}>' for id in self.red_team])} ({self.red_side.title()})\n"
                    f"Blue Team: {', '.join([f'<@{id}>' for id in self.blue_team])} ({self.blue_side.title()})\n\n"
                    f"Voice Channels:\n"
                    f"🔴 Red Team: {red_vc.mention}\n"
                    f"🔵 Blue Team: {blue_vc.mention}\n\n"
                    f"Captains, please submit the match score:"
                ),
                view=score_view,
            )


class ScoreSubmissionView(discord.ui.View):
    def __init__(self, match_id: str, red_team: List[str], blue_team: List[str]):
        super().__init__(timeout=None)
        self.match_id = match_id
        self.red_team = red_team
        self.blue_team = blue_team
        self.red_score: Optional[int] = None
        self.blue_score: Optional[int] = None

    @discord.ui.button(label="Submit Red Team Score", style=discord.ButtonStyle.danger)
    async def submit_red_score(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if str(interaction.user.id) not in self.red_team:
            await interaction.response.send_message(
                "Only Red Team members can submit their score!", ephemeral=True
            )
            return

        modal = ScoreModal("Red Team Score")
        await interaction.response.send_modal(modal)
        await modal.wait()

        try:
            self.red_score = int(modal.score.value)
            await self.check_scores(interaction)
        except ValueError:
            await interaction.followup.send(
                "Please enter a valid number!", ephemeral=True
            )

    @discord.ui.button(
        label="Submit Blue Team Score", style=discord.ButtonStyle.primary
    )
    async def submit_blue_score(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if str(interaction.user.id) not in self.blue_team:
            await interaction.response.send_message(
                "Only Blue Team members can submit their score!", ephemeral=True
            )
            return

        modal = ScoreModal("Blue Team Score")
        await interaction.response.send_modal(modal)
        await modal.wait()

        try:
            self.blue_score = int(modal.score.value)
            await self.check_scores(interaction)
        except ValueError:
            await interaction.followup.send(
                "Please enter a valid number!", ephemeral=True
            )

    async def check_scores(self, interaction: discord.Interaction):
        if self.red_score is not None and self.blue_score is not None:
            if self.red_score == self.blue_score:
                admin_role = discord.utils.get(interaction.guild.roles, name="Admin")
                if admin_role:
                    await interaction.channel.send(
                        f"{admin_role.mention} Score discrepancy detected!\n"
                        f"Red Team submitted: {self.red_score}\n"
                        f"Blue Team submitted: {self.blue_score}"
                    )
            else:
                # TODO: Update stats and leaderboard
                await interaction.channel.send(
                    f"**Match Complete!**\n"
                    f"Red Team: {self.red_score}\n"
                    f"Blue Team: {self.blue_score}"
                )


class ScoreModal(discord.ui.Modal, title="Submit Match Score"):
    score = discord.ui.TextInput(
        label="Enter the score",
        placeholder="Enter the number of rounds won",
        required=True,
    )

    def __init__(self, title: str):
        super().__init__(title=title)


class QueueCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_matches = {}

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

    async def create_match(self, guild: discord.Guild, rank_group: str):
        queue = get_queue(rank_group)
        if not queue or len(queue.players) < 10:
            return

        players = queue.players[:10]
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

        match_id = f"match_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        match_category = await guild.create_category(match_id)

        match_channel = await match_category.create_text_channel(name="match-info")

        general_vc = await match_category.create_voice_channel(
            name="General", user_limit=10
        )

        captains = random.sample([p.discord_id for p in players], 2)

        self.active_matches[match_id] = {
            "channel": match_channel,
            "players": players,
            "captains": captains,
            "general_vc": general_vc,
        }

        view = TeamSelectionView(match_id, players, captains)

        initial_message = await match_channel.send(
            f"**New Match Created!**\n"
            f"Players: {', '.join([f'<@{p.discord_id}>' for p in players])}\n\n"
            f"Captains:\n"
            f"🔴 Red Team: <@{captains[0]}>\n"
            f"🔵 Blue Team: <@{captains[1]}>\n\n"
            f"Voice Channel: {general_vc.mention}\n"
            f"Team selection will begin now!",
            view=view,
        )

        await view.update_selection_message(initial_message)

    async def end_selection(self, interaction: discord.Interaction):
        side_view = SideSelectionView(self.match_id, self.red_team, self.blue_team)

        await interaction.message.edit(
            content=(
                f"**Team Selection Complete!**\n\n"
                f"🔴 Red Team: {', '.join([f'<@{id}>' for id in self.red_team])}\n"
                f"🔵 Blue Team: {', '.join([f'<@{id}>' for id in self.blue_team])}\n\n"
                f"Red Team Captain (<@{self.captains[0]}>) please select your side:"
            ),
            view=side_view,
        )


async def setup(bot):
    await bot.add_cog(QueueCog(bot))
