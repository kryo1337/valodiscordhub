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
from utils.db import get_player, add_to_queue, remove_from_queue, get_queue, remove_player_from_queue

load_dotenv()
GUILD_ID = int(os.getenv("DISCORD_GUILD_ID", "0"))

class QueueView(discord.ui.View):
    def __init__(self, rank_group: str):
        super().__init__(timeout=None)
        self.rank_group = rank_group
        
    @discord.ui.button(label="Join Queue", style=discord.ButtonStyle.primary, custom_id="join_button")
    async def join_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        player = get_player(str(interaction.user.id))
        
        if not player:
            await interaction.response.send_message(
                "You need to register first using `/rank` command!",
                ephemeral=True
            )
            return

        queue = get_queue(self.rank_group)
        player_in_queue = any(p.discord_id == str(interaction.user.id) for p in queue.players)

        if player_in_queue:
            queue = remove_player_from_queue(self.rank_group, str(interaction.user.id))
            await interaction.response.send_message("You have left the queue!", ephemeral=True)
        else:
            queue = add_to_queue(self.rank_group, str(interaction.user.id))
            await interaction.response.send_message("You have joined the queue!", ephemeral=True)

        player_in_queue = any(p.discord_id == str(interaction.user.id) for p in queue.players)
        button.label = "Leave Queue" if player_in_queue else "Join Queue"
        button.style = discord.ButtonStyle.danger if player_in_queue else discord.ButtonStyle.primary

        await interaction.message.edit(
            content=f"**{self.rank_group.upper()} Queue**\n"
                   f"Click the button to join/leave the queue!\n"
                   f"Current players in queue: {len(queue.players)}\n"
                   f"Players: {', '.join([f'<@{p.discord_id}>' for p in queue.players])}",
            view=self
        )

        if len(queue.players) >= 10:
            cog = interaction.client.get_cog("QueueCog")
            if cog:
                await cog.create_match(interaction.guild, self.rank_group)

class TeamSelectionView(discord.ui.View):
    def __init__(self, match_id: str, players: List[QueueEntry], captains: List[str]):
        super().__init__(timeout=None)
        self.match_id = match_id
        self.players = players
        self.captains = captains
        self.current_captain_index = 0
        self.red_team: List[str] = []
        self.blue_team: List[str] = []
        self.side_selected = False
        self.selection_order = [1, 2, 3, 5, 7, 9]
        self.current_selection_index = 0

    @discord.ui.button(label="Select Player", style=discord.ButtonStyle.primary)
    async def select_player(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.captains[self.current_captain_index]:
            await interaction.response.send_message("It's not your turn to select!", ephemeral=True)
            return

        available_players = [p for p in self.players if p.discord_id not in self.red_team + self.blue_team]
        if not available_players:
            await interaction.response.send_message("No players available to select!", ephemeral=True)
            return

        select_menu = discord.ui.Select(
            placeholder="Select a player",
            options=[
                discord.SelectOption(
                    label=f"Player {i+1}",
                    value=p.discord_id,
                    description=f"<@{p.discord_id}>"
                ) for i, p in enumerate(available_players)
            ]
        )

        async def select_callback(interaction: discord.Interaction):
            selected_id = select_menu.values[0]
            if self.current_captain_index == 0:
                self.red_team.append(selected_id)
            else:
                self.blue_team.append(selected_id)

            self.current_selection_index += 1
            if self.current_selection_index >= len(self.selection_order):
                await self.end_selection(interaction)
            else:
                self.current_captain_index = 1 - self.current_captain_index
                await self.update_selection_message(interaction)

        select_menu.callback = select_callback
        view = discord.ui.View()
        view.add_item(select_menu)

        await interaction.response.send_message("Select a player:", view=view, ephemeral=True)

    @discord.ui.button(label="Select Side", style=discord.ButtonStyle.secondary)
    async def select_side(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.captains[self.current_captain_index]:
            await interaction.response.send_message("It's not your turn to select!", ephemeral=True)
            return

        side_menu = discord.ui.Select(
            placeholder="Select your side",
            options=[
                discord.SelectOption(label="Attack", value="attack"),
                discord.SelectOption(label="Defense", value="defense")
            ]
        )

        async def side_callback(interaction: discord.Interaction):
            selected_side = side_menu.values[0]
            self.side_selected = True
            await self.update_selection_message(interaction)

        side_menu.callback = side_callback
        view = discord.ui.View()
        view.add_item(side_menu)

        await interaction.response.send_message("Select your side:", view=view, ephemeral=True)

    async def update_selection_message(self, interaction: discord.Interaction):
        current_captain = self.captains[self.current_captain_index]
        message = (
            f"**Team Selection in Progress**\n\n"
            f"Current Captain: <@{current_captain}>\n"
            f"Selection Order: {self.selection_order[self.current_selection_index]}/10\n\n"
            f"Red Team: {', '.join([f'<@{id}>' for id in self.red_team])}\n"
            f"Blue Team: {', '.join([f'<@{id}>' for id in self.blue_team])}\n\n"
            f"Available Players: {', '.join([f'<@{p.discord_id}>' for p in self.players if p.discord_id not in self.red_team + self.blue_team])}"
        )
        await interaction.message.edit(content=message)

    async def end_selection(self, interaction: discord.Interaction):
        if not self.side_selected:
            self.side_selected = True
            random.choice(["attack", "defense"])

        category = interaction.channel.category
        red_vc = await interaction.guild.create_voice_channel(
            name="Red Team",
            category=category
        )
        blue_vc = await interaction.guild.create_voice_channel(
            name="Blue Team",
            category=category
        )

        score_view = ScoreSubmissionView(self.match_id, self.red_team, self.blue_team)
        
        await interaction.message.edit(
            content=(
                f"**Team Selection Complete!**\n\n"
                f"Red Team: {', '.join([f'<@{id}>' for id in self.red_team])}\n"
                f"Blue Team: {', '.join([f'<@{id}>' for id in self.blue_team])}\n\n"
                f"Voice Channels:\n"
                f"🔴 Red Team: {red_vc.mention}\n"
                f"🔵 Blue Team: {blue_vc.mention}\n\n"
                f"Captains, please submit the match score:"
            ),
            view=score_view
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
    async def submit_red_score(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) not in self.red_team:
            await interaction.response.send_message("Only Red Team members can submit their score!", ephemeral=True)
            return

        modal = ScoreModal("Red Team Score")
        await interaction.response.send_modal(modal)
        await modal.wait()
        
        try:
            self.red_score = int(modal.score.value)
            await self.check_scores(interaction)
        except ValueError:
            await interaction.followup.send("Please enter a valid number!", ephemeral=True)

    @discord.ui.button(label="Submit Blue Team Score", style=discord.ButtonStyle.primary)
    async def submit_blue_score(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) not in self.blue_team:
            await interaction.response.send_message("Only Blue Team members can submit their score!", ephemeral=True)
            return

        modal = ScoreModal("Blue Team Score")
        await interaction.response.send_modal(modal)
        await modal.wait()
        
        try:
            self.blue_score = int(modal.score.value)
            await self.check_scores(interaction)
        except ValueError:
            await interaction.followup.send("Please enter a valid number!", ephemeral=True)

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
        required=True
    )

    def __init__(self, title: str):
        super().__init__(title=title)

class QueueCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_matches = {}

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
        
        rank_groups = ["iron-plat", "dia-asc", "imm1-radiant"]
        for rank_group in rank_groups:
            overwrites = {
                interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
                interaction.guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True)
            }
            
            role = discord.utils.get(interaction.guild.roles, name=rank_group)
            if role:
                overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)
            
            channel = await category.create_text_channel(
                name=f"queue-{rank_group}",
                overwrites=overwrites
            )
            
            view = QueueView(rank_group)
            
            await channel.send(
                f"**{rank_group.upper()} Queue**\n"
                f"Click the button to join/leave the queue!\n"
                f"Current players in queue: 0",
                view=view
            )

        await interaction.followup.send("✅ Queue channels have been set up!", ephemeral=True)

    async def create_match(self, guild: discord.Guild, rank_group: str):
        players = remove_from_queue(rank_group)
        
        category = discord.utils.get(guild.categories, name="Queue")
        match_channel = await guild.create_text_channel(
            name=f"match-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
            category=category
        )
        
        # TODO: Get top 2 players
        captains = random.sample([p.discord_id for p in players], 2)
        
        match_id = f"match_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.active_matches[match_id] = {
            "channel": match_channel,
            "players": players,
            "captains": captains
        }
        
        view = TeamSelectionView(match_id, players, captains)
        
        await match_channel.send(
            f"**New Match Created!**\n"
            f"Players: {', '.join([f'<@{p.discord_id}>' for p in players])}\n\n"
            f"Captains:\n"
            f"🔴 Red Team: <@{captains[0]}>\n"
            f"🔵 Blue Team: <@{captains[1]}>\n\n"
            f"Team selection will begin in 30 seconds...",
            view=view
        )
        
        await asyncio.sleep(30)
        await view.update_selection_message(await match_channel.fetch_message(match_channel.last_message_id))

async def setup(bot):
    await bot.add_cog(QueueCog(bot)) 