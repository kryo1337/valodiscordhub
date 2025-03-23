import discord
from discord.ext import commands
from typing import List, Optional
from datetime import datetime
import asyncio
import random
import logging
from db.models.queue import QueueEntry

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
        self.selection_message = None
        self.timeout_task = None
        self.last_picker = None
        logger.info(f"TeamSelectionView initialized for match {match_id}")

    async def update_selection_message(self, message: discord.Message):
        logger.info(f"Updating selection message for match {self.match_id}")
        self.selection_message = message
        current_captain = self.captains[self.current_captain_index]
        remaining_players = len([p for p in self.players if p.discord_id not in self.red_team + self.blue_team])

        message_content = (
            f"**Team Selection in Progress**\n\n"
            f"🔴 Red Team Captain: <@{self.captains[0]}>\n"
            f"🔵 Blue Team Captain: <@{self.captains[1]}>\n\n"
            f"Current Captain's Turn: <@{current_captain}>\n"
            f"Selection: {self.current_selection_index + 1}/8\n"
            f"Players Remaining: {remaining_players}\n"
            f"Time remaining: 15 seconds\n\n"
            f"Red Team: {', '.join([f'<@{id}>' for id in self.red_team])}\n"
            f"Blue Team: {', '.join([f'<@{id}>' for id in self.blue_team])}\n\n"
            f"Available Players: {', '.join([f'<@{p.discord_id}>' for p in self.players if p.discord_id not in self.red_team + self.blue_team])}"
        )
        await message.edit(content=message_content)

        select_menu = discord.ui.Select(
            placeholder="Select a player",
            options=[
                discord.SelectOption(
                    label=f"Player {i+1}",
                    value=p.discord_id,
                    description=f"<@{p.discord_id}>",
                )
                for i, p in enumerate([p for p in self.players if p.discord_id not in self.red_team + self.blue_team])
            ],
        )

        async def select_callback(interaction: discord.Interaction):
            if str(interaction.user.id) != current_captain:
                await interaction.response.send_message("It's not your turn to select!", ephemeral=True)
                return
            selected_id = select_menu.values[0]
            await self.select_callback(interaction, selected_id)
            try:
                await interaction.message.delete()
            except:
                pass
            await interaction.response.defer()

        select_menu.callback = select_callback
        view = discord.ui.View()
        view.add_item(select_menu)

        selection_message = await message.channel.send(
            f"<@{current_captain}> Select a player:",
            view=view
        )

        await asyncio.sleep(15)
        try:
            await selection_message.delete()
        except:
            pass

        await self.start_timeout()

    async def on_timeout(self):
        logger.info(f"Timeout triggered for match {self.match_id}")
        if self.selection_message:
            available_players = [p for p in self.players if p.discord_id not in self.red_team + self.blue_team]
            if available_players:
                selected_player = random.choice(available_players)
                logger.info(f"Auto-selected player {selected_player.discord_id} for team {self.current_captain_index}")
                
                if self.current_captain_index == 0:
                    self.red_team.append(selected_player.discord_id)
                else:
                    self.blue_team.append(selected_player.discord_id)

                self.current_selection_index += 1
                self.last_picker = self.current_captain_index
                logger.info(f"Selection index updated to {self.current_selection_index}")
                
                if self.current_selection_index >= len(self.selection_order):
                    logger.info("All players selected, ending selection")
                    await self.end_selection(self.selection_message)
                else:
                    self.current_captain_index = 1 - self.current_captain_index
                    logger.info(f"Switching to captain {self.current_captain_index}")
                    await self.update_selection_message(self.selection_message)

    async def start_timeout(self):
        logger.info(f"Starting timeout for match {self.match_id}")
        if self.timeout_task:
            self.timeout_task.cancel()
        self.timeout_task = asyncio.create_task(self._timeout_handler())

    async def _timeout_handler(self):
        try:
            await asyncio.sleep(15)
            await self.on_timeout()
        except asyncio.CancelledError:
            pass

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
        logger.info(f"SideSelectionView initialized for match {match_id}")

    async def update_message(self, message: discord.Message):
        logger.info(f"Updating side selection message for match {self.match_id}")
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
                try:
                    await self.timeout_task
                except asyncio.CancelledError:
                    pass
            if str(interaction.user.id) in self.red_team:
                self.red_side = "attack"
                logger.info(f"Red team selected Attack side")
            else:
                self.blue_side = "attack"
                logger.info(f"Blue team selected Attack side")
            self.last_message = interaction.message
            await self.check_sides(interaction)
            await interaction.response.defer()

        async def defense_callback(interaction: discord.Interaction):
            if str(interaction.user.id) != self.side_selector_id:
                await interaction.response.send_message("Only the team captain can select sides!", ephemeral=True)
                return
            if self.timeout_task:
                self.timeout_task.cancel()
                try:
                    await self.timeout_task
                except asyncio.CancelledError:
                    pass
            if str(interaction.user.id) in self.red_team:
                self.red_side = "defense"
                logger.info(f"Red team selected Defense side")
            else:
                self.blue_side = "defense"
                logger.info(f"Blue team selected Defense side")
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
        logger.info(f"Side selection timeout triggered for match {self.match_id}")
        if not self.red_side:
            self.red_side = random.choice(["attack", "defense"])
            logger.info(f"Randomly selected Red side: {self.red_side}")
        if not self.blue_side:
            self.blue_side = "defense" if self.red_side == "attack" else "attack"
            logger.info(f"Randomly selected Blue side: {self.blue_side}")

        if self.last_message:
            await self.check_sides(self.last_message)

    async def start_timeout(self):
        logger.info(f"Starting side selection timeout for match {self.match_id}")
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
        logger.info(f"Checking sides for match {self.match_id}")
        if self.red_side and self.blue_side:
            try:
                match_category = interaction.channel.category
                if not match_category:
                    logger.error(f"No category found for match {self.match_id}")
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

                logger.info(f"Created voice channels for match {self.match_id}")

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

                logger.info(f"Updated message with voice channels for match {self.match_id}")
            except Exception as e:
                logger.error(f"Error creating voice channels: {str(e)}", exc_info=True)
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

class MatchCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_matches = {}

    async def create_match(self, guild: discord.Guild, rank_group: str, players: List[QueueEntry]):
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
            f"🔴 Red Team Captain: <@{captains[0]}>\n"
            f"🔵 Blue Team Captain: <@{captains[1]}>\n\n"
            f"Voice Channel: {general_vc.mention}\n"
            f"Team selection will begin now!",
            view=view,
        )

        await view.update_selection_message(initial_message)

async def setup(bot):
    await bot.add_cog(MatchCog(bot)) 