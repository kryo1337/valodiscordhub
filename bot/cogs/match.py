import discord
from discord.ext import commands
from typing import List, Optional, Union
from datetime import datetime
import asyncio
import random
from db.models.queue import QueueEntry
from utils.db import update_match_defense, get_match, update_match_teams, update_match_result
from utils.db import create_match as create_match_db
from utils.db import get_leaderboard_page, update_leaderboard, get_leaderboard
from db.models.leaderboard import LeaderboardEntry
from .leaderboard import LeaderboardCog


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
        available_players = [p for p in self.players if p.discord_id not in self.red_team + self.blue_team]
        remaining_players = len(available_players)

        if self.current_selection_index >= len(self.selection_order):
            return

        current_captain = self.captains[self.current_captain_index]
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
        if available_players and self.current_selection_index < len(self.selection_order) - 1:
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
                if self.current_selection_index < len(self.selection_order) - 1:
                    await self.update_selection_message(message)
                await interaction.response.defer()

            select_menu.callback = select_callback
            view.add_item(select_menu)

        await message.edit(content=message_content, view=view)

        if available_players and self.current_selection_index < len(self.selection_order) - 1:
            await self.start_timeout()

    async def select_callback(self, interaction: discord.Interaction, selected_id: str):
        if self.current_captain_index == 0:
            self.red_team.append(selected_id)
        else:
            self.blue_team.append(selected_id)

        self.current_selection_index += 1
        self.last_picker = self.current_captain_index

        available_players = [p for p in self.players if p.discord_id not in self.red_team + self.blue_team]
        if len(available_players) == 1:
            await self.assign_last_player(available_players[0].discord_id)
        elif self.current_selection_index >= len(self.selection_order):
            await self.end_selection(interaction.channel)
        else:
            self.current_captain_index = 1 - self.current_captain_index
            await self.update_selection_message(self.selection_message)

    async def assign_last_player(self, last_player_id: str):
        if self.last_picker == 0:
            self.blue_team.append(last_player_id)
        else:
            self.red_team.append(last_player_id)

        self.current_selection_index += 1
        await self.end_selection(self.selection_message.channel)

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
        available_players = [p for p in self.players if p.discord_id not in self.red_team + self.blue_team]

        if len(available_players) == 1:
            await self.assign_last_player(available_players[0].discord_id)
            return

        selected_player = random.choice(available_players)
        if self.current_captain_index == 0:
            self.red_team.append(selected_player.discord_id)
        else:
            self.blue_team.append(selected_player.discord_id)

        self.current_selection_index += 1
        self.last_picker = self.current_captain_index

        available_players = [p for p in self.players if p.discord_id not in self.red_team + self.blue_team]
        if len(available_players) == 1:
            await self.assign_last_player(available_players[0].discord_id)
        elif self.current_selection_index >= len(self.selection_order):
            await self.end_selection(self.selection_message.channel)
        else:
            self.current_captain_index = 1 - self.current_captain_index
            await self.update_selection_message(self.selection_message)

    async def end_selection(self, channel: discord.abc.Messageable):
        guild = channel.guild
        match_category = discord.utils.get(guild.categories, name=self.match_id)

        update_match_teams(
            match_id=self.match_id,
            players_red=self.red_team,
            players_blue=self.blue_team
        )

        lobby_vc = discord.utils.get(guild.voice_channels, name="Lobby", category=match_category)
        if lobby_vc:
            await lobby_vc.delete()

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(connect=False),
            guild.me: discord.PermissionOverwrite(connect=True, manage_channels=True),
        }
        # for member_id in self.red_team:
        #     member = guild.get_member(int(member_id))
        #     if member:
        #         overwrites[member] = discord.PermissionOverwrite(connect=True)

        red_vc = await guild.create_voice_channel(
            name="Red Team",
            category=match_category,
            overwrites=overwrites,
            user_limit=5
        )

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(connect=False),
            guild.me: discord.PermissionOverwrite(connect=True, manage_channels=True),
        }
        # for member_id in self.blue_team:
        #     member = guild.get_member(int(member_id))
        #     if member:
        #         overwrites[member] = discord.PermissionOverwrite(connect=True)

        blue_vc = await guild.create_voice_channel(
            name="Blue Team",
            category=match_category,
            overwrites=overwrites,
            user_limit=5
        )

        side_selector_id = self.captains[1 - self.last_picker]
        side_view = SideSelectionView(self.match_id, self.red_team, self.blue_team, side_selector_id, red_vc, blue_vc)

        if self.selection_message:
            await side_view.update_message(self.selection_message)
        else:
            await channel.send("Error: Selection message not found. Proceeding with new message.")
            new_message = await channel.send("Starting side selection...")
            await side_view.update_message(new_message)


class SideSelectionView(discord.ui.View):
    def __init__(self, match_id: str, red_team: List[str], blue_team: List[str], side_selector_id: str, red_vc: discord.VoiceChannel, blue_vc: discord.VoiceChannel):
        super().__init__(timeout=None)
        self.match_id = match_id
        self.red_team = red_team
        self.blue_team = blue_team
        self.side_selector_id = side_selector_id
        self.red_vc = red_vc
        self.blue_vc = blue_vc
        self.red_side = None
        self.blue_side = None
        self.timeout_task = None
        self.last_message = None

    async def update_message(self, message: discord.Message):
        self.last_message = message
        side_selector_team = "Red" if self.side_selector_id in self.red_team else "Blue"

        match = get_match(self.match_id)

        message_content = (
            f"**Team Selection Complete!**\n\n"
            f"**Captains:**\n"
            f"🔴 Red Team Captain: <@{self.red_team[0]}>\n"
            f"🔵 Blue Team Captain: <@{self.blue_team[0]}>\n"
            f"**Teams:**\n"
            f"🔴 Red Team: {', '.join([f'<@{id}>' for id in self.red_team])}\n"
            f"🔵 Blue Team: {', '.join([f'<@{id}>' for id in self.blue_team])}\n\n"
            f"**Voice Channels:**\n"
            f"🔴 Red Team: {self.red_vc.mention}\n"
            f"🔵 Blue Team: {self.blue_vc.mention}\n\n"
            f"🎮 Lobby Master: <@{match.lobby_master}>\n\n"
            f"**Side Selection:**\n"
            f"{side_selector_team} Team Captain (<@{self.side_selector_id}>), please select your side:\n"
            f"Time remaining: 30 seconds"
        )

        view = discord.ui.View()
        
        attack_button = discord.ui.Button(label="Attack", style=discord.ButtonStyle.primary)
        defense_button = discord.ui.Button(label="Defense", style=discord.ButtonStyle.secondary)

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
            await self.check_sides(interaction)
            await interaction.response.defer()

        attack_button.callback = attack_callback
        defense_button.callback = defense_callback
        view.add_item(attack_button)
        view.add_item(defense_button)

        await message.edit(content=message_content, view=view)

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
        await asyncio.sleep(30)
        await self.on_timeout()

    async def check_sides(self, interaction: Union[discord.Interaction, discord.Message]):
        if self.red_side and self.blue_side:
            update_match_defense(
                match_id=self.match_id,
                defense_start="red" if self.red_side == "defense" else "blue"
            )
            
            match = get_match(self.match_id)

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
                f"🔴 Red Team: {self.red_vc.mention}\n"
                f"🔵 Blue Team: {self.blue_vc.mention}\n\n"
                f"🎮 Lobby Master: <@{match.lobby_master}>\n\n"
                f"**Score Submission:**\n"
                f"Captains, please submit the match score:"
            )

            if isinstance(interaction, discord.Message):
                await interaction.edit(content=message_content, view=score_view)
            else:
                await interaction.message.edit(content=message_content, view=score_view)

class ScoreSubmissionView(discord.ui.View):
    def __init__(self, match_id: str, red_team: List[str], blue_team: List[str]):
        super().__init__(timeout=None)
        self.match_id = match_id
        self.red_team = red_team
        self.blue_team = blue_team
        self.red_score: Optional[tuple] = None
        self.blue_score: Optional[tuple] = None
        self.red_captain = red_team[0]
        self.blue_captain = blue_team[0]

    @discord.ui.button(label="Submit Red Team Score", style=discord.ButtonStyle.danger)
    async def submit_red_score(self, interaction: discord.Interaction, _: discord.ui.Button):
        if str(interaction.user.id) != self.red_captain:
            await interaction.response.send_message("Only the Red Team captain can submit the score!", ephemeral=True)
            return
        modal = ScoreModal("Red Team Score", self, "red")
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Submit Blue Team Score", style=discord.ButtonStyle.primary)
    async def submit_blue_score(self, interaction: discord.Interaction, _: discord.ui.Button):
        if str(interaction.user.id) != self.blue_captain:
            await interaction.response.send_message("Only the Blue Team captain can submit the score!", ephemeral=True)
            return
        modal = ScoreModal("Blue Team Score", self, "blue")
        await interaction.response.send_modal(modal)

    def validate_score(self, score: int) -> bool:
        return 0 <= score <= 13

    async def update_leaderboard_points(self, interaction: discord.Interaction, winner: str):
        match = get_match(self.match_id)
        rank_group = match.rank_group

        leaderboard = get_leaderboard(rank_group)
        current_entries = {str(p.discord_id): p for p in leaderboard.players}
        updated_entries = []

        all_match_players = self.red_team + self.blue_team
        player_ranks = {p.discord_id: p.rank for p in match.players}

        winning_team = self.red_team if winner == "red" else self.blue_team
        for player_id in winning_team:
            if player_id in current_entries:
                entry = current_entries[player_id]
                entry.points += 10
                entry.matches_played += 1
                entry.winrate = (entry.winrate * (entry.matches_played - 1) + 100) / entry.matches_played
                entry.streak = max(0, entry.streak) + 1
            else:
                entry = LeaderboardEntry(
                    discord_id=player_id,
                    rank=player_ranks.get(player_id, "Unranked"),
                    points=1010,
                    matches_played=1,
                    winrate=100.0,
                    streak=1
                )
            updated_entries.append(entry)

        losing_team = self.blue_team if winner == "red" else self.red_team
        for player_id in losing_team:
            if player_id in current_entries:
                entry = current_entries[player_id]
                entry.points = max(0, entry.points - 10) 
                entry.matches_played += 1
                entry.winrate = (entry.winrate * (entry.matches_played - 1)) / entry.matches_played
                entry.streak = min(0, entry.streak) - 1
            else:
                entry = LeaderboardEntry(
                    discord_id=player_id,
                    rank=player_ranks.get(player_id, "Unranked"),
                    points=990,
                    matches_played=1,
                    winrate=0.0,
                    streak=-1
                )
            updated_entries.append(entry)

        update_leaderboard(rank_group, updated_entries)

        stats_cog = interaction.client.get_cog("StatsCog")
        if stats_cog:
            for channel_id in stats_cog.stats_channels:
                channel = interaction.client.get_channel(channel_id)
                if channel:
                    await stats_cog.update_player_stats(channel, all_match_players)

        history_cog = interaction.client.get_cog("HistoryCog")
        if history_cog:
            await history_cog.add_match_to_history(match)

        leaderboard_cog = interaction.client.get_cog("LeaderboardCog")
        if leaderboard_cog:
            await leaderboard_cog.update_leaderboard()

    async def check_scores(self, interaction: discord.Interaction):
        if self.red_score is not None and self.blue_score is not None:
            if not self.validate_score(self.red_score) or not self.validate_score(self.blue_score):
                await interaction.channel.send("Invalid scores submitted! Scores must be between 0 and 13.")
                self.red_score = None
                self.blue_score = None
                return

            if self.red_score != self.blue_score:
                admin_role = discord.utils.get(interaction.guild.roles, name="Admin")
                await interaction.channel.send(
                    f"{admin_role.mention} Score discrepancy detected!\n"
                    f"🔴 Red Team Captain <@{self.red_captain}> submitted: {self.red_score[0]}-{self.red_score[1]}\n"
                    f"🔵 Blue Team Captain <@{self.blue_captain}> submitted: {self.blue_score[0]}-{self.blue_score[1]}\n"
                    f"Please verify the correct score."
                )
            else:
                red_score, blue_score = self.red_score
                winner = "red" if red_score > blue_score else "blue"
                
                update_match_result(
                    match_id=self.match_id,
                    red_score=red_score,
                    blue_score=blue_score,
                    result=winner
                )

                await self.update_leaderboard_points(interaction, winner)

                await interaction.channel.send(
                    f"**Match Complete!**\n"
                    f"Scores verified by both captains:\n"
                    f"🔴 Red Team: {red_score}\n"
                    f"🔵 Blue Team: {blue_score}\n"
                    f"**{winner.title()} Team Wins!**"
                )
                
                await asyncio.sleep(10)
                await self.cleanup_match_channels(interaction.guild)

    async def cleanup_match_channels(self, guild: discord.Guild):
        try:
            match_category = discord.utils.get(guild.categories, name=self.match_id)
            if match_category:
                for channel in match_category.channels:
                    await channel.delete(reason="Match completed")
                
                await match_category.delete(reason="Match completed")
        except Exception as e:
            print(f"Error cleaning up match channels: {e}")

class ScoreModal(discord.ui.Modal):
    def __init__(self, title: str, view: ScoreSubmissionView, team: str):
        super().__init__(title=title)
        self.view = view
        self.team = team
        self.team_score = discord.ui.TextInput(
            label="Your team's score",
            placeholder="Enter your team's rounds won (0-13)",
            required=True,
        )
        self.opponent_score = discord.ui.TextInput(
            label="Opponent's score",
            placeholder="Enter opponent's rounds won (0-13)",
            required=True,
        )
        self.add_item(self.team_score)
        self.add_item(self.opponent_score)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            team_score = int(self.team_score.value)
            opponent_score = int(self.opponent_score.value)
            
            if not self.view.validate_score(team_score) or not self.view.validate_score(opponent_score):
                await interaction.response.send_message("Invalid scores! Scores must be between 0 and 13.", ephemeral=True)
                return

            if self.team == "red":
                self.view.red_score = (team_score, opponent_score)
            else:
                self.view.blue_score = (team_score, opponent_score)

            await self.view.check_scores(interaction)
            await interaction.response.send_message("Score submitted!", ephemeral=True)
        except ValueError:
            await interaction.response.send_message("Please enter valid numbers!", ephemeral=True)

async def create_match(guild: discord.Guild, rank_group: str, players: List[QueueEntry]):
    match_id = f"match_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    match_category = await guild.create_category(match_id)

    match_channel = await match_category.create_text_channel(name="Match")

    match_vc = await match_category.create_voice_channel(
        name="Lobby", user_limit=10
    )
    
    leaderboard = get_leaderboard(rank_group)
    
    player_ids = [p.discord_id for p in players]
    
    leaderboard_players = []
    for player in leaderboard.players:
        if player.discord_id in player_ids:
            leaderboard_players.append(player)
    
    sorted_leaderboard_players = sorted(leaderboard_players, key=lambda x: x.points, reverse=True)
    
    if len(sorted_leaderboard_players) >= 2:
        captains = [sorted_leaderboard_players[0].discord_id, sorted_leaderboard_players[1].discord_id]
    else:
        leaderboard_ids = [p.discord_id for p in sorted_leaderboard_players]
        remaining_players = [pid for pid in player_ids if pid not in leaderboard_ids]
        
        if sorted_leaderboard_players and remaining_players:
            captains = [sorted_leaderboard_players[0].discord_id]
            captains.append(random.choice(remaining_players))
        else:
            captains = random.sample(player_ids, 2)
   
    lobby_master = random.choice(captains)
    
    create_match_db(
        match_id=match_id,
        players_red=[],
        players_blue=[],
        captain_red=captains[0],
        captain_blue=captains[1],
        lobby_master=lobby_master,
        rank_group=rank_group
    )
    
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

    await asyncio.sleep(10)
    await view.update_selection_message(initial_message)

class MatchCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_matches = {}

async def setup(bot):
    await bot.add_cog(MatchCog(bot))