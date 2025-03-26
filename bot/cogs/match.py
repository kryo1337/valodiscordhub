import discord
from discord.ext import commands
from typing import List, Optional
from datetime import datetime
import asyncio
import random
from db.models.queue import QueueEntry
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TeamSelectionView(discord.ui.View):
    def __init__(self, match_id: str, players: List[QueueEntry], captains: List[str]):
        super().__init__(timeout=None)
        self.match_id = match_id
        self.players = players
        self.captains = captains
        self.current_captain_index = 0
        self.red_team: List[str] = [captains[0]]
        self.blue_team: List[str] = [captains[1]]
        self.selection_order = [1, 2, 3, 4, 5, 6, 7, 8]
        self.current_selection_index = 0
        self.selection_message: discord.Message = None
        self.timeout_task: asyncio.Task = None
        self.last_picker: int = None

    async def update_selection_message(self, message: discord.Message):
        self.selection_message = message
        current_captain = self.captains[self.current_captain_index]
        available_players = [p for p in self.players if p.discord_id not in self.red_team + self.blue_team]
        remaining_players = len(available_players)

        message_content = (
            f"**Team Selection in Progress**\n\n"
            f"🔴 Red Team Captain: <@{self.captains[0]}>\n"
            f"🔵 Blue Team Captain: <@{self.captains[1]}>\n\n"
            f"Current Captain's Turn: <@{current_captain}>\n"
            f"Selection: {self.current_selection_index + 1}/{len(self.selection_order)}\n"
            f"Players Remaining: {remaining_players}\n"
            f"Time remaining: 15 seconds\n\n"
            f"🔴 Red Team: {', '.join([f'<@{id}>' for id in self.red_team])}\n"
            f"🔵 Blue Team: {', '.join([f'<@{id}>' for id in self.blue_team])}\n\n"
            f"Available Players: {', '.join([f'<@{p.discord_id}>' for p in available_players]) if available_players else 'None'}"
        )

        view = discord.ui.View()
        if available_players:
            select_menu = discord.ui.Select(
                placeholder="Select a player",
                options=[
                    discord.SelectOption(
                        label=f"Player {i + 1}",
                        value=p.discord_id,
                        description=f"<@{p.discord_id}>",
                    )
                    for i, p in enumerate(available_players)
                ],
            )

            async def select_callback(interaction: discord.Interaction):
                if str(interaction.user.id) != current_captain:
                    await interaction.response.send_message("It's not your turn to select!", ephemeral=True)
                    return
                selected_id = select_menu.values[0]
                if self.timeout_task:
                    self.timeout_task.cancel()
                await self.select_callback(interaction, selected_id)
                await self.update_selection_message(message)

            select_menu.callback = select_callback
            view.add_item(select_menu)

        try:
            await message.edit(content=message_content, view=view)
        except discord.HTTPException as e:
            logging.error(f"Failed to edit selection message: {e}")
            return

        if available_players:
            await self.start_timeout()

    async def select_callback(self, interaction: discord.Interaction, selected_id: str):
        if self.current_captain_index == 0:
            self.red_team.append(selected_id)
        else:
            self.blue_team.append(selected_id)

        self.current_selection_index += 1
        self.last_picker = self.current_captain_index

        if self.current_selection_index >= len(self.selection_order):
            await self.end_selection(interaction.channel)
        else:
            self.current_captain_index = 1 - self.current_captain_index
            await self.update_selection_message(self.selection_message)

    async def start_timeout(self):
        if self.timeout_task:
            self.timeout_task.cancel()
        self.timeout_task = asyncio.create_task(self._timeout_handler())

    async def _timeout_handler(self):
        try:
            await asyncio.sleep(15)
            await self.on_timeout()
        except asyncio.CancelledError:
            pass

    async def on_timeout(self):
        if not self.selection_message:
            return

        available_players = [p for p in self.players if p.discord_id not in self.red_team + self.blue_team]
        if available_players:
            selected_player = random.choice(available_players)
            if self.current_captain_index == 0:
                self.red_team.append(selected_player.discord_id)
            else:
                self.blue_team.append(selected_player.discord_id)

            self.current_selection_index += 1
            self.last_picker = self.current_captain_index

            if self.current_selection_index >= len(self.selection_order):
                await self.end_selection(self.selection_message.channel)
            else:
                self.current_captain_index = 1 - self.current_captain_index
                await self.update_selection_message(self.selection_message)

    async def end_selection(self, channel: discord.abc.Messageable):
        side_selector_id = self.captains[1 - self.last_picker]
        side_view = SideSelectionView(self.match_id, self.red_team, self.blue_team, side_selector_id)

        completion_message = (
            f"**Team Selection Complete!**\n\n"
            f"🔴 Red Team: {', '.join([f'<@{id}>' for id in self.red_team])}\n"
            f"🔵 Blue Team: {', '.join([f'<@{id}>' for id in self.blue_team])}\n\n"
            f"Next: Side selection by <@{side_selector_id}>"
        )

        try:
            await self.selection_message.edit(content=completion_message, view=None)
            await side_view.update_message(self.selection_message)
        except discord.HTTPException as e:
            logging.error(f"Failed to transition to side selection: {e}")

class SideSelectionView(discord.ui.View):
    def __init__(self, match_id: str, red_team: List[str], blue_team: List[str], side_selector_id: str):
        super().__init__(timeout=None)
        self.match_id = match_id
        self.red_team = red_team
        self.blue_team = blue_team
        self.side_selector_id = side_selector_id
        self.red_side = None
        self.blue_side = None
        self.timeout_task = None
        self.last_message = None

    async def update_message(self, message: discord.Message):
        self.last_message = message
        side_selector_team = "Red" if self.side_selector_id in self.red_team else "Blue"

        message_content = (
            f"**Team Selection Complete!**\n\n"
            f"**Captains:**\n"
            f"🔴 Red Team Captain: <@{self.red_team[0]}>\n"
            f"🔵 Blue Team Captain: <@{self.blue_team[0]}>\n\n"
            f"**Teams:**\n"
            f"🔴 Red Team: {', '.join([f'<@{id}>' for id in self.red_team])}\n"
            f"🔵 Blue Team: {', '.join([f'<@{id}>' for id in self.blue_team])}\n\n"
            f"**Side Selection:**\n"
            f"{side_selector_team} Team Captain (<@{self.side_selector_id}>), please select your side:"
        )
        await message.edit(content=message_content)

        view = discord.ui.View()
        
        attack_button = discord.ui.Button(label="Select Attack", style=discord.ButtonStyle.primary)
        defense_button = discord.ui.Button(label="Select Defense", style=discord.ButtonStyle.secondary)

        async def attack_callback(interaction: discord.Interaction):
            if str(interaction.user.id) != self.side_selector_id:
                await interaction.response.send_message("Only the team captain can select sides!", ephemeral=True)
                return
            if self.timeout_task:
                self.timeout_task.cancel()
            if str(interaction.user.id) in self.red_team:
                self.red_side = "attack"
                self.blue_side = "defense"
            else:
                self.blue_side = "attack"
                self.red_side = "defense"
            self.last_message = interaction.message
            await self.check_sides(interaction)
            await interaction.response.defer()

        async def defense_callback(interaction: discord.Interaction):
            if str(interaction.user.id) != self.side_selector_id:
                await interaction.response.send_message("Only the team captain can select sides!", ephemeral=True)
                return
            if self.timeout_task:
                self.timeout_task.cancel()
            if str(interaction.user.id) in self.red_team:
                self.red_side = "defense"
                self.blue_side = "attack"
            else:
                self.blue_side = "defense"
                self.red_side = "attack"
            self.last_message = interaction.message
            await self.check_sides(interaction)
            await interaction.response.defer()

        attack_button.callback = attack_callback
        defense_button.callback = defense_callback

        view.add_item(attack_button)
        view.add_item(defense_button)

        await message.channel.send(
            f"<@{self.side_selector_id}> Select your side:",
            view=view
        )
        await self.start_timeout()

    async def on_timeout(self):
        if not self.red_side or not self.blue_side:
            self.red_side = random.choice(["attack", "defense"])
            self.blue_side = "defense" if self.red_side == "attack" else "attack"

        if self.last_message:
            await self.check_sides(self.last_message)

    async def start_timeout(self):
        if self.timeout_task:
            self.timeout_task.cancel()
        self.timeout_task = asyncio.create_task(self._timeout_handler())

    async def _timeout_handler(self):
        try:
            await asyncio.sleep(15)
            await self.on_timeout()
        except asyncio.CancelledError:
            pass

    async def check_sides(self, interaction: discord.Interaction):
        if self.red_side and self.blue_side:
            try:
                match_category = interaction.channel.category
                if not match_category:
                    raise ValueError("Match category not found")

                overwrites = {
                    interaction.guild.default_role: discord.PermissionOverwrite(connect=False),
                    interaction.guild.me: discord.PermissionOverwrite(connect=True, manage_channels=True),
                }
                for member_id in self.red_team:
                    member = interaction.guild.get_member(int(member_id))
                    if member:
                        overwrites[member] = discord.PermissionOverwrite(connect=True)

                red_vc = await interaction.guild.create_voice_channel(
                    name=f"Red Team ({self.red_side.title()})",
                    category=match_category,
                    overwrites=overwrites,
                    user_limit=5
                )

                overwrites = {
                    interaction.guild.default_role: discord.PermissionOverwrite(connect=False),
                    interaction.guild.me: discord.PermissionOverwrite(connect=True, manage_channels=True),
                }
                for member_id in self.blue_team:
                    member = interaction.guild.get_member(int(member_id))
                    if member:
                        overwrites[member] = discord.PermissionOverwrite(connect=True)

                blue_vc = await interaction.guild.create_voice_channel(
                    name=f"Blue Team ({self.blue_side.title()})",
                    category=match_category,
                    overwrites=overwrites,
                    user_limit=5
                )

                score_view = ScoreSubmissionView(self.match_id, self.red_team, self.blue_team)
                
                message_content = (
                    f"**Match Setup Complete!**\n\n"
                    f"**Captains:**\n"
                    f"🔴 Red Team Captain: <@{self.red_team[0]}>\n"
                    f"🔵 Blue Team Captain: <@{self.blue_team[0]}>\n\n"
                    f"**Teams:**\n"
                    f"🔴 Red Team: {', '.join([f'<@{id}>' for id in self.red_team])} ({self.red_side.title()})\n"
                    f"🔵 Blue Team: {', '.join([f'<@{id}>' for id in self.blue_team])} ({self.blue_side.title()})\n\n"
                    f"**Voice Channels:**\n"
                    f"🔴 Red Team: {red_vc.mention} (5 players max)\n"
                    f"🔵 Blue Team: {blue_vc.mention} (5 players max)\n\n"
                    f"**Score Submission:**\n"
                    f"Captains, please submit the match score:"
                )

                if isinstance(interaction, discord.Message):
                    await interaction.edit(content=message_content, view=score_view)
                else:
                    await interaction.message.edit(content=message_content, view=score_view)

            except Exception as e:
                score_view = ScoreSubmissionView(self.match_id, self.red_team, self.blue_team)
                error_message = (
                    f"**Error creating voice channels!**\n\n"
                    f"**Teams:**\n"
                    f"🔴 Red Team: {', '.join([f'<@{id}>' for id in self.red_team])} ({self.red_side.title()})\n"
                    f"🔵 Blue Team: {', '.join([f'<@{id}>' for id in self.blue_team])} ({self.blue_side.title()})\n\n"
                    f"Please contact an administrator to create the voice channels manually."
                )

                if isinstance(interaction, discord.Message):
                    await interaction.edit(content=error_message, view=score_view)
                else:
                    await interaction.message.edit(content=error_message, view=score_view)

class ScoreSubmissionView(discord.ui.View):
    def __init__(self, match_id: str, red_team: List[str], blue_team: List[str]):
        super().__init__(timeout=None)
        self.match_id = match_id
        self.red_team = red_team
        self.blue_team = blue_team
        self.red_score: Optional[int] = None
        self.blue_score: Optional[int] = None

    @discord.ui.button(label="Submit Red Team Score", style=discord.ButtonStyle.danger)
    async def submit_red_score(self, interaction: discord.Interaction, _: discord.ui.Button):
        if str(interaction.user.id) not in self.red_team:
            await interaction.response.send_message("Only Red Team members can submit their score!", ephemeral=True)
            return
        modal = ScoreModal("Red Team Score", self)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Submit Blue Team Score", style=discord.ButtonStyle.primary)
    async def submit_blue_score(self, interaction: discord.Interaction, _: discord.ui.Button):
        if str(interaction.user.id) not in self.blue_team:
            await interaction.response.send_message("Only Blue Team members can submit their score!", ephemeral=True)
            return
        modal = ScoreModal("Blue Team Score", self)
        await interaction.response.send_modal(modal)

    async def check_scores(self, interaction: discord.Interaction):
        if self.red_score is not None and self.blue_score is not None:
            if self.red_score == self.blue_score:
                admin_role = discord.utils.get(interaction.guild.roles, name="Admin")
                if admin_role:
                    await interaction.channel.send(
                        f"{admin_role.mention} Score discrepancy detected!\n"
                        f"🔴 Red Team submitted: {self.red_score}\n"
                        f"🔵 Blue Team submitted: {self.blue_score}"
                    )
            else:
                await interaction.channel.send(
                    f"**Match Complete!**\n"
                    f"🔴 Red Team: {self.red_score}\n"
                    f"🔵 Blue Team: {self.blue_score}"
                )

class ScoreModal(discord.ui.Modal):
    def __init__(self, title: str, view: ScoreSubmissionView):
        super().__init__(title=title)
        self.view = view
        self.score = discord.ui.TextInput(
            label="Enter the score",
            placeholder="Enter the number of rounds won",
            required=True,
        )
        self.add_item(self.score)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            score = int(self.score.value)
            if str(interaction.user.id) in self.view.red_team:
                self.view.red_score = score
            elif str(interaction.user.id) in self.view.blue_team:
                self.view.blue_score = score
            await self.view.check_scores(interaction)
            await interaction.response.send_message("Score submitted!", ephemeral=True)
        except ValueError:
            await interaction.response.send_message("Please enter a valid number!", ephemeral=True)

async def create_match(guild: discord.Guild, rank_group: str, players: List[QueueEntry]):
    match_id = f"match_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    match_category = await guild.create_category(match_id)

    match_channel = await match_category.create_text_channel(name="match-info")

    match_vc = await match_category.create_voice_channel(
        name=f"VC - {match_id}", user_limit=10
    )

    captains = random.sample([p.discord_id for p in players], 2)
    
    view = TeamSelectionView(match_id, players, captains)
    
    initial_message = await match_channel.send(
        f"**New Match Created!**\n"
        f"Players: {', '.join([f'<@{p.discord_id}>' for p in players])}\n\n"
        f"Captains:\n"
        f"🔴 Red Team Captain: <@{captains[0]}>\n"
        f"🔵 Blue Team Captain: <@{captains[1]}>\n\n"
        f"Voice Channel: {match_vc.mention}\n"
        f"Team selection will begin now!",
        view=view,
    )

    await view.update_selection_message(initial_message)

class MatchCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_matches = {}

async def setup(bot):
    await bot.add_cog(MatchCog(bot))