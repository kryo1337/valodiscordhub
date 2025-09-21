import discord
from discord.ext import commands
from typing import List, Optional, Union
from datetime import datetime
import asyncio
import random
from models.queue import QueueEntry
from utils.db import update_match_defense, get_match, update_match_teams, update_match_result, update_match_maps
from utils.db import create_match as create_match_db, get_next_match_id, calculate_mmr_points
from utils.db import get_leaderboard_page, update_leaderboard, get_leaderboard, get_player
from utils.db import update_match_result, add_admin_log
from models.leaderboard import LeaderboardEntry
from .leaderboard import LeaderboardCog
import time

CAPTAIN_VOTING_TIME = 30
PLAYER_SELECTION_TIME = 15
MAP_BAN_TIME = 15
SIDE_SELECTION_TIME = 15
AFK_CHECK_TIME = 300


class AFKCheckView(discord.ui.View):
    def __init__(self, match_id: str, players: List[QueueEntry], rank_group: str, lobby_vc: discord.VoiceChannel, match_cog=None):
        super().__init__(timeout=AFK_CHECK_TIME)
        self.match_id = match_id
        self.players = players
        self.rank_group = rank_group
        self.lobby_vc = lobby_vc
        self.message = None
        self.afk_check_end_time = int(time.time()) + AFK_CHECK_TIME
        self.check_complete = False
        self.match_cog = match_cog
        
        if self.match_cog:
            self.match_cog.afk_checks[match_id] = self

    async def update_afk_message(self):
        if not self.message:
            return

        voice_members = {str(member.id) for member in self.lobby_vc.members}
        player_ids = {p.discord_id for p in self.players}
        
        joined_players = [p for p in self.players if p.discord_id in voice_members]
        missing_players = [p for p in self.players if p.discord_id not in voice_members]

        embed = discord.Embed(
            title="🎤 AFK Check - Join Voice Channel",
            description=f"**All players must join {self.lobby_vc.mention} to continue!**\n\n⏱️ **Time remaining: <t:{self.afk_check_end_time}:R>**",
            color=discord.Color.dark_theme()
        )

        if missing_players:
            embed.add_field(
                name="❌ Missing Players",
                value="\n".join([f"• <@{p.discord_id}>" for p in missing_players]),
                inline=False
            )

        embed.add_field(
            name="Status",
            value=f"**{len(joined_players)}/{len(self.players)}** players joined",
            inline=False
        )

        embed.set_footer(text="Players who don't join will be replaced or timed out!")

        await self.message.edit(embed=embed, view=self)

        if len(missing_players) == 0:
            await self.complete_afk_check()

    @discord.ui.button(label="🚀 Force Start Voting (Testing)", style=discord.ButtonStyle.success)
    async def force_start_voting(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        
        self.check_complete = True
        
        if self.match_cog and self.match_id in self.match_cog.afk_checks:
            del self.match_cog.afk_checks[self.match_id]
        
        await asyncio.sleep(1)
        await self.start_captain_voting(self.players)

    async def on_timeout(self):
        if not self.check_complete:
            await self.handle_afk_timeout()

    async def handle_afk_timeout(self):
        voice_members = {str(member.id) for member in self.lobby_vc.members}
        missing_players = [p for p in self.players if p.discord_id not in voice_members]
        
        if missing_players:
            embed = discord.Embed(
                title="⚠️ AFK Check Failed",
                description="Some players failed to join the voice channel.",
                color=discord.Color.red()
            )
            
            embed.add_field(
                name="Missing Players",
                value="\n".join([f"• <@{p.discord_id}>" for p in missing_players]),
                inline=False
            )

            # TODO: Replace missing players with queue players
            # TODO: Timeout missing players for 3 hours
            # # Timeout missing players
            # for player in missing_players:
            #     await timeout_player(player.discord_id, duration_minutes=180, reason="AFK during match setup")

            embed.add_field(
                name="Action Required",
                value="❌ **Match cancelled** - Not enough active players.\n*(Replacement system not implemented yet)*",
                inline=False
            )

            await self.message.edit(embed=embed, view=None)
            
            if self.match_cog and self.match_cog.bot:
                admin_cog = self.match_cog.bot.get_cog("AdminCog")
                if admin_cog:
                    try:
                        await update_match_result(
                            match_id=self.match_id,
                            red_score=None,
                            blue_score=None,
                            result="cancelled"
                        )
                        
                        await add_admin_log(
                            action="cancel_match",
                            admin_discord_id="system",
                            match_id=self.match_id,
                            reason="Match cancelled due to AFK players"
                        )
                        
                        await admin_cog.cleanup_match_channels(self.message.guild, self.match_id)
                    except Exception as e:
                        print(f"Error cancelling match: {e}")
        else:
            await self.complete_afk_check()

    async def complete_afk_check(self):
        self.check_complete = True
        
        if self.match_cog and self.match_id in self.match_cog.afk_checks:
            del self.match_cog.afk_checks[self.match_id]
        
        voice_members = {str(member.id) for member in self.lobby_vc.members}
        missing_players = [p for p in self.players if p.discord_id not in voice_members]
        
        if len(missing_players) == 0:
            await asyncio.sleep(1)
            await self.start_captain_voting(self.players)
        else:
            embed = discord.Embed(
                title="❌ Match Cancelled",
                description="Not enough active players to continue.",
                color=discord.Color.red()
            )
            await self.message.edit(embed=embed, view=None)
            
            if self.match_cog and self.match_cog.bot:
                admin_cog = self.match_cog.bot.get_cog("AdminCog")
                if admin_cog:
                    try:
                        await update_match_result(
                            match_id=self.match_id,
                            red_score=None,
                            blue_score=None,
                            result="cancelled"
                        )
                        
                        await add_admin_log(
                            action="cancel_match",
                            admin_discord_id="system",
                            match_id=self.match_id,
                            reason="Match cancelled due to insufficient players"
                        )
                        
                        await admin_cog.cleanup_match_channels(self.message.guild, self.match_id)
                    except Exception as e:
                        print(f"Error cancelling match: {e}")

    async def start_captain_voting(self, active_players: List[QueueEntry]):
        voting_view = CaptainVotingView(self.match_id, active_players, self.rank_group)
        voting_view.message = self.message
        await voting_view.update_voting_message()


class CaptainVotingView(discord.ui.View):
    def __init__(self, match_id: str, players: List[QueueEntry], rank_group: str):
        super().__init__(timeout=CAPTAIN_VOTING_TIME)
        self.match_id = match_id
        self.players = players
        self.rank_group = rank_group
        self.votes_highest = set()
        self.votes_random = set()
        self.required_votes = 6
        self.total_players = len(players)
        self.voting_complete = False
        self.message = None
        self.captains = None
        self.voting_end_time = int(time.time()) + CAPTAIN_VOTING_TIME

    @discord.ui.button(label="2 Highest Rated Players", style=discord.ButtonStyle.primary, emoji="⭐")
    async def vote_highest(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = str(interaction.user.id)
        
        if user_id not in [p.discord_id for p in self.players]:
            await interaction.response.send_message("You are not part of this match!", ephemeral=True)
            return
        
        self.votes_random.discard(user_id)
        self.votes_highest.add(user_id)
        
        await interaction.response.defer()
        await self.update_voting_message()
        await self.check_vote_completion()

    @discord.ui.button(label="Random Players", style=discord.ButtonStyle.secondary, emoji="🎲")
    async def vote_random(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = str(interaction.user.id)
        
        if user_id not in [p.discord_id for p in self.players]:
            await interaction.response.send_message("You are not part of this match!", ephemeral=True)
            return
        
        self.votes_highest.discard(user_id)
        self.votes_random.add(user_id)
        
        await interaction.response.defer()
        await self.update_voting_message()
        await self.check_vote_completion()

    async def update_voting_message(self):
        if not self.message:
            return

        embed = discord.Embed(
            title="Captain Selection Voting",
            description="Vote for how captains should be selected!",
            color=discord.Color.dark_theme()
        )
        
        total_votes = len(self.votes_highest) + len(self.votes_random)
        progress = int((total_votes / self.total_players) * 10)
        progress_bar = "▰" * progress + "▱" * (10 - progress)
        
        embed.add_field(
            name="Voting Progress",
            value=f"`{progress_bar}` {total_votes}/{self.total_players} votes",
            inline=False
        )
        
        embed.add_field(
            name="⭐ 2 Highest Rated Players",
            value=f"**{len(self.votes_highest)} votes** ({len(self.votes_highest)}/{self.required_votes} needed)\n" + 
                  ("\n".join([f"• <@{uid}>" for uid in self.votes_highest]) if self.votes_highest else "No votes yet"),
            inline=True
        )
        
        embed.add_field(
            name="🎲 Random Players",
            value=f"**{len(self.votes_random)} votes** ({len(self.votes_random)}/{self.required_votes} needed)\n" + 
                  ("\n".join([f"• <@{uid}>" for uid in self.votes_random]) if self.votes_random else "No votes yet"),
            inline=True
        )
        
        voted_users = self.votes_highest | self.votes_random
        non_voters = [p.discord_id for p in self.players if p.discord_id not in voted_users]
        
        if non_voters:
            embed.add_field(
                name="Haven't Voted Yet",
                value="\n".join([f"• <@{uid}>" for uid in non_voters[:10]]),
                inline=False
            )
        
        embed.add_field(
            name="⏱️ Time Remaining",
            value=f"Voting ends <t:{self.voting_end_time}:R>",
            inline=False
        )
        
        embed.set_footer(text="6/10 votes needed")
        
        await self.message.edit(embed=embed, view=self)

    async def check_vote_completion(self):
        if self.voting_complete:
            return
            
        if len(self.votes_highest) >= self.required_votes:
            self.voting_complete = True
            await self.complete_voting("highest")
        elif len(self.votes_random) >= self.required_votes:
            self.voting_complete = True
            await self.complete_voting("random")

    async def on_timeout(self):
        if not self.voting_complete:
            self.voting_complete = True
            await self.complete_voting("highest")

    async def complete_voting(self, result: str):
        if result == "highest":
            self.captains = await self.get_highest_rated_captains()
            method = "⭐ **2 Highest Rated Players**"
        else:
            self.captains = await self.get_random_captains()
            method = "🎲 **Random Players**"
        
        embed = discord.Embed(
            title="Captain Selection Complete!",
            description=f"Selection method: {method}",
            color=discord.Color.dark_theme()
        )
        
        embed.add_field(
            name="Selected Captains",
            value=f"🔴 Red Team Captain: <@{self.captains[0]}>\n🔵 Blue Team Captain: <@{self.captains[1]}>",
            inline=False
        )
        
        for item in self.children:
            item.disabled = True
        
        await self.message.edit(embed=embed, view=self)
        
        lobby_master = random.choice(self.captains)
        await self.update_match_captains(lobby_master)
        
        await asyncio.sleep(3)
        await self.start_team_selection()

    async def get_highest_rated_captains(self):
        leaderboard = await get_leaderboard(self.rank_group)
        player_ids = [p.discord_id for p in self.players]
        
        leaderboard_players = []
        for player in leaderboard.players:
            if player.discord_id in player_ids:
                leaderboard_players.append(player)
        
        sorted_leaderboard_players = sorted(leaderboard_players, key=lambda x: x.points, reverse=True)
        
        if len(sorted_leaderboard_players) >= 2:
            return [sorted_leaderboard_players[0].discord_id, sorted_leaderboard_players[1].discord_id]
        else:
            return await self.get_random_captains()

    async def get_random_captains(self):
        player_ids = [p.discord_id for p in self.players]
        return random.sample(player_ids, 2)

    async def update_match_captains(self, lobby_master: str):
        from utils.api_client import api_client
        
        update_data = {
            "captain_red": self.captains[0],
            "captain_blue": self.captains[1],
            "lobby_master": lobby_master
        }
        
        try:
            await api_client.patch(f"/matches/{self.match_id}", update_data)
        except Exception as e:
            print(f"Error updating match captains: {e}")

    async def start_team_selection(self):
        view = TeamSelectionView(self.match_id, self.players, self.captains)
        
        embed = discord.Embed(
            title="Team Selection",
            color=discord.Color.dark_theme()
        )
        
        embed.add_field(
            name="Captains",
            value=f"🔴 Red Team Captain: <@{self.captains[0]}>\n🔵 Blue Team Captain: <@{self.captains[1]}>",
            inline=False
        )
        
        embed.add_field(
            name="Players",
            value="\n".join([f"• <@{p.discord_id}>" for p in self.players]),
            inline=False
        )
        
        await self.message.edit(embed=embed, view=view)
        await view.update_selection_message(self.message)


class TeamSelectionView(discord.ui.View):
    def __init__(self, match_id: str, players: List[QueueEntry], captains: List[str]):
        super().__init__(timeout=None)
        self.match_id = match_id
        self.players = players
        self.captains = captains
        self.current_captain_index = 0
        self.red_team: List[str] = [captains[0]]
        self.blue_team: List[str] = [captains[1]]
        self.selection_pattern = [
            (0, 1), 
            (1, 2), 
            (0, 2), 
            (1, 2), 
        ]
        self.current_pattern_index = 0
        self.picks_remaining_for_current_captain = 1 
        self.current_selection_index = 0
        self.total_picks = 8 
        self.selection_message: discord.Message = None
        self.timeout_task: asyncio.Task = None
        self.last_picker: int = None
        self.selection_end_time = None

    async def update_selection_message(self, message: discord.Message):
        self.selection_message = message
        available_players = [p for p in self.players if p.discord_id not in self.red_team + self.blue_team]
        remaining_players = len(available_players)

        if self.current_selection_index >= self.total_picks:
            return

        if available_players and self.current_selection_index < self.total_picks:
            self.selection_end_time = int(time.time()) + PLAYER_SELECTION_TIME

        current_captain = self.captains[self.current_captain_index]
        
        embed = discord.Embed(
            title="Team Selection",
            color=discord.Color.dark_theme()
        )
        
        progress = "▰" * (self.current_selection_index + 1) + "▱" * (self.total_picks - self.current_selection_index - 1)
        
        captain_name = "Red" if self.current_captain_index == 0 else "Blue"
        embed.add_field(
            name="Progress",
            value=f"`{progress}`\nSelection {self.current_selection_index + 1}/{self.total_picks}\n{captain_name} Captain: {self.picks_remaining_for_current_captain} picks remaining",
            inline=False
        )
        
        embed.add_field(
            name=f"🔴 Red Team",
            value=f"• Captain: <@{self.red_team[0]}>\n" + "\n".join([f"• <@{id}>" for id in self.red_team[1:]]),
            inline=True
        )
        embed.add_field(
            name=f"🔵 Blue Team",
            value=f"• Captain: <@{self.blue_team[0]}>\n" + "\n".join([f"• <@{id}>" for id in self.blue_team[1:]]),
            inline=True
        )
        
        embed.add_field(
            name="Current Turn",
            value=f"<@{current_captain}>",
            inline=False
        )
        
        if available_players:
            embed.add_field(
                name="Available Players",
                value="\n".join([f"• <@{p.discord_id}>" for p in available_players]),
                inline=False
            )
        
        if self.selection_end_time:
            embed.add_field(
                name="⏱️ Time Remaining",
                value=f"Selection ends <t:{self.selection_end_time}:R>",
                inline=False
            )
        
        embed.set_footer(text=f"Players remaining: {remaining_players}")

        view = discord.ui.View()
        if available_players and self.current_selection_index < self.total_picks - 1:
            select_menu = discord.ui.Select(
                placeholder="Select a player",
                options=[
                    discord.SelectOption(
                        label=message.guild.get_member(int(p.discord_id)).display_name if p.discord_id.isdigit() else p.discord_id,
                        value=p.discord_id,
                        description=f"<@{p.discord_id}>",
                    )
                    for i, p in enumerate(available_players)
                ],
            )

            async def select_callback(interaction: discord.Interaction):
                if str(interaction.user.id) != current_captain:
                    if str(interaction.user.id) in self.captains:
                        await interaction.response.send_message("It's not your turn to select!", ephemeral=True)
                    else:
                        await interaction.response.send_message("❌ You are not a captain! Only captains can select players.", ephemeral=True)
                    return
                selected_id = select_menu.values[0]
                if self.timeout_task:
                    self.timeout_task.cancel()
                await self.select_callback(interaction, selected_id)
                if self.current_selection_index < self.total_picks - 1:
                    await self.update_selection_message(message)
                await interaction.response.defer()

            select_menu.callback = select_callback
            view.add_item(select_menu)

        await message.edit(embed=embed, view=view)

        if available_players and self.current_selection_index < self.total_picks:
            await self.start_timeout()

    async def select_callback(self, interaction: discord.Interaction, selected_id: str):
        if self.current_captain_index == 0:
            self.red_team.append(selected_id)
        else:
            self.blue_team.append(selected_id)

        self.current_selection_index += 1
        self.picks_remaining_for_current_captain -= 1
        self.last_picker = self.current_captain_index

        available_players = [p for p in self.players if p.discord_id not in self.red_team + self.blue_team]
        if len(available_players) == 1:
            await self.assign_last_player(available_players[0].discord_id)
        elif self.current_selection_index >= self.total_picks:
            await self.end_selection(interaction.channel)
        else:
            if self.picks_remaining_for_current_captain == 0:
                self.current_pattern_index += 1
                if self.current_pattern_index < len(self.selection_pattern):
                    self.current_captain_index, self.picks_remaining_for_current_captain = self.selection_pattern[self.current_pattern_index]
                
            self.selection_end_time = int(time.time()) + PLAYER_SELECTION_TIME
            await self.update_selection_message(self.selection_message)

    async def assign_last_player(self, last_player_id: str):
        self.red_team.append(last_player_id)
        self.current_selection_index += 1
        await self.end_selection(self.selection_message.channel)

    async def start_timeout(self):
        if self.timeout_task:
            self.timeout_task.cancel()
        self.timeout_task = asyncio.create_task(self._timeout_handler())

    async def _timeout_handler(self):
        try:
            await asyncio.sleep(PLAYER_SELECTION_TIME)
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
            if selected_player.discord_id not in self.red_team and selected_player.discord_id not in self.blue_team:
                self.red_team.append(selected_player.discord_id)
        else:
            if selected_player.discord_id not in self.red_team and selected_player.discord_id not in self.blue_team:
                self.blue_team.append(selected_player.discord_id)

        self.current_selection_index += 1
        self.picks_remaining_for_current_captain -= 1
        self.last_picker = self.current_captain_index

        available_players = [p for p in self.players if p.discord_id not in self.red_team + self.blue_team]
        
        if len(available_players) == 1:
            await self.assign_last_player(available_players[0].discord_id)
        elif self.current_selection_index >= self.total_picks:
            await self.end_selection(self.selection_message.channel)
        else:
            if self.picks_remaining_for_current_captain == 0:
                self.current_pattern_index += 1
                if self.current_pattern_index < len(self.selection_pattern):
                    self.current_captain_index, self.picks_remaining_for_current_captain = self.selection_pattern[self.current_pattern_index]
                    
            self.selection_end_time = int(time.time()) + PLAYER_SELECTION_TIME
            await self.update_selection_message(self.selection_message)

    async def end_selection(self, channel: discord.abc.Messageable):
        guild = channel.guild
        match_category = discord.utils.get(guild.categories, name=self.match_id)

        await update_match_teams(
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
        for member_id in self.red_team:
            try:
                member = guild.get_member(int(member_id))
                if member:
                    overwrites[member] = discord.PermissionOverwrite(connect=True)
            except (ValueError, TypeError):
                print(f"Could not get member for ID: {member_id}")

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
        for member_id in self.blue_team:
            try:
                member = guild.get_member(int(member_id))
                if member:
                    overwrites[member] = discord.PermissionOverwrite(connect=True)
            except (ValueError, TypeError):
                print(f"Could not get member for ID: {member_id}")

        blue_vc = await guild.create_voice_channel(
            name="Blue Team",
            category=match_category,
            overwrites=overwrites,
            user_limit=5
        )

        map_ban_starter = 0 
        map_view = MapBanningView(self.match_id, self.red_team, self.blue_team, self.captains, map_ban_starter, red_vc, blue_vc)

        if self.selection_message:
            await map_view.update_message(self.selection_message)
        else:
            await channel.send("Error: Selection message not found. Proceeding with new message.")
            new_message = await channel.send("Starting map banning...")
            await map_view.update_message(new_message)


class MapBanningView(discord.ui.View):
    def __init__(self, match_id: str, red_team: List[str], blue_team: List[str], captains: List[str], ban_starter: int, red_vc: discord.VoiceChannel, blue_vc: discord.VoiceChannel):
        super().__init__(timeout=None)
        self.match_id = match_id
        self.red_team = red_team
        self.blue_team = blue_team
        self.captains = captains
        self.red_vc = red_vc
        self.blue_vc = blue_vc
        
        self.maps = ["Abyss", "Ascent", "Bind", "Corrode", "Haven", "Lotus", "Sunset"]
        self.banned_maps = []
        self.selected_map = None
        
        self.current_banner = ban_starter
        self.bans_completed = 0
        self.max_bans = 6
        self.timeout_task = None
        self.last_message = None
        self.ban_end_time = None

    async def update_message(self, message: discord.Message):
        self.last_message = message
        
        available_maps = [m for m in self.maps if m not in self.banned_maps]
        if available_maps and self.bans_completed < self.max_bans:
            self.ban_end_time = int(time.time()) + MAP_BAN_TIME
        
        if self.bans_completed >= self.max_bans:
            remaining_maps = [m for m in self.maps if m not in self.banned_maps]
            if remaining_maps:
                self.selected_map = remaining_maps[0]
                await self.complete_map_selection()
            return

        current_captain = self.captains[self.current_banner]
        current_team = "Red" if self.current_banner == 0 else "Blue"
        
        embed = discord.Embed(
            title="Map Banning",
            color=discord.Color.dark_theme()
        )
        
        progress = "▰" * (self.bans_completed + 1) + "▱" * (self.max_bans - self.bans_completed - 1)
        embed.add_field(
            name="Progress",
            value=f"`{progress}`\nBan {self.bans_completed + 1}/{self.max_bans}",
            inline=False
        )
        
        embed.add_field(
            name=f"🔴 Red Team",
            value=f"• Captain: <@{self.red_team[0]}>\n" + "\n".join([f"• <@{id}>" for id in self.red_team[1:]]),
            inline=True
        )
        embed.add_field(
            name=f"🔵 Blue Team",
            value=f"• Captain: <@{self.blue_team[0]}>\n" + "\n".join([f"• <@{id}>" for id in self.blue_team[1:]]),
            inline=True
        )
        
        embed.add_field(
            name="Current Turn",
            value=f"<@{current_captain}>",
            inline=False
        )
        
        available_maps = [m for m in self.maps if m not in self.banned_maps]
        if available_maps:
            embed.add_field(
                name="Available Maps",
                value="\n".join([f"• {m}" for m in available_maps]),
                inline=False
            )
        
        if self.banned_maps:
            embed.add_field(
                name="Banned Maps",
                value="\n".join([f"~~{m}~~" for m in self.banned_maps]),
                inline=False
            )
        
        if self.ban_end_time:
            embed.add_field(
                name="⏱️ Time Remaining",
                value=f"Ban phase ends <t:{self.ban_end_time}:R>",
                inline=False
            )

        view = discord.ui.View()
        if available_maps and self.bans_completed < self.max_bans:
            for i, map_name in enumerate(available_maps):
                if i >= 25:
                    break
                button = discord.ui.Button(
                    label=f"Ban {map_name}",
                    style=discord.ButtonStyle.danger,
                    custom_id=f"ban_{map_name}"
                )
                
                async def ban_callback(interaction: discord.Interaction, map_to_ban=map_name):
                    if str(interaction.user.id) != current_captain:
                        if str(interaction.user.id) in self.captains:
                            await interaction.response.send_message("It's not your turn to ban!", ephemeral=True)
                        else:
                            await interaction.response.send_message("❌ You are not a captain! Only captains can ban maps.", ephemeral=True)
                        return
                    
                    if self.timeout_task:
                        self.timeout_task.cancel()
                    
                    await self.ban_map(interaction, map_to_ban)
                
                button.callback = ban_callback
                view.add_item(button)

        await message.edit(embed=embed, view=view)

        if available_maps and self.bans_completed < self.max_bans:
            await self.start_timeout()

    async def ban_map(self, interaction: discord.Interaction, map_name: str):
        self.banned_maps.append(map_name)
        self.bans_completed += 1
        
        self.current_banner = 1 - self.current_banner
        
        await interaction.response.defer()
        
        if self.bans_completed >= self.max_bans:
            await self.complete_map_selection()
        else:
            self.ban_end_time = int(time.time()) + MAP_BAN_TIME
            await self.update_message(self.last_message)

    async def complete_map_selection(self):
        remaining_maps = [m for m in self.maps if m not in self.banned_maps]
        if remaining_maps:
            self.selected_map = remaining_maps[0]
        
        await update_match_maps(self.match_id, self.banned_maps, self.selected_map)
        
        side_selector_id = self.captains[self.current_banner]
        side_view = SideSelectionView(self.match_id, self.red_team, self.blue_team, side_selector_id, self.red_vc, self.blue_vc)
        
        await side_view.update_message(self.last_message)

    async def start_timeout(self):
        if self.timeout_task:
            self.timeout_task.cancel()
        self.timeout_task = asyncio.create_task(self._timeout_handler())

    async def _timeout_handler(self):
        try:
            await asyncio.sleep(MAP_BAN_TIME)
            await self.on_timeout()
        except asyncio.CancelledError:
            pass

    async def on_timeout(self):
        available_maps = [m for m in self.maps if m not in self.banned_maps]
        if available_maps:
            map_to_ban = random.choice(available_maps)
            self.banned_maps.append(map_to_ban)
            self.bans_completed += 1
            self.current_banner = 1 - self.current_banner
            
            if self.bans_completed >= self.max_bans:
                await self.complete_map_selection()
            else:
                self.ban_end_time = int(time.time()) + MAP_BAN_TIME
                await self.update_message(self.last_message)


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
        self.side_end_time = None

    async def attack_callback(self, interaction: discord.Interaction):
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

    async def defense_callback(self, interaction: discord.Interaction):
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

    async def update_message(self, message: discord.Message):
        self.last_message = message
        side_selector_team = "Red" if self.side_selector_id in self.red_team else "Blue"
        match = await get_match(self.match_id)
        
        embed = discord.Embed(
            title="Side Selection",
            description=f"🗺️ **Map: {match.selected_map or 'Unknown'}**",
            color=discord.Color.dark_theme()
        )

        red_status = f"⚔️ Attack" if self.red_side == "attack" else f"🛡️ Defense" if self.red_side == "defense" else ""
        blue_status = f"⚔️ Attack" if self.blue_side == "attack" else f"🛡️ Defense" if self.blue_side == "defense" else ""
        
        embed.add_field(
            name=f"🔴 Red Team {red_status}",
            value=f"• Captain: <@{self.red_team[0]}>\n" + "\n".join([f"• <@{id}>" for id in self.red_team[1:]]),
            inline=True
        )
        embed.add_field(
            name=f"🔵 Blue Team {blue_status}",
            value=f"• Captain: <@{self.blue_team[0]}>\n" + "\n".join([f"• <@{id}>" for id in self.blue_team[1:]]),
            inline=True
        )
        
        if not self.red_side and not self.blue_side:
            if not self.side_end_time:
                self.side_end_time = int(time.time()) + SIDE_SELECTION_TIME
                
            embed.add_field(
                name="Side Selection",
                value=f"{side_selector_team} Team Captain (<@{self.side_selector_id}>), please select your side:",
                inline=False
            )
        
        embed.add_field(
            name="Voice Channels",
            value=f"🔴 {self.red_vc.mention}\n🔵 {self.blue_vc.mention}",
            inline=False
        )
        
        embed.add_field(
            name="🎮 Lobby Master",
            value=f"<@{match.lobby_master}>",
            inline=False
        )
        
        if not self.red_side and not self.blue_side and self.side_end_time:
            embed.add_field(
                name="⏱️ Time Remaining",
                value=f"Side selection ends <t:{self.side_end_time}:R>",
                inline=False
            )

        view = discord.ui.View()
        
        if not self.red_side and not self.blue_side:
            attack_button = discord.ui.Button(
                label="Attack",
                style=discord.ButtonStyle.success,
                emoji="⚔️"
            )
            defense_button = discord.ui.Button(
                label="Defense",
                style=discord.ButtonStyle.danger,
                emoji="🛡️"
            )

            attack_button.callback = self.attack_callback
            defense_button.callback = self.defense_callback
            
            view.add_item(attack_button)
            view.add_item(defense_button)

        await message.edit(embed=embed, view=view)

        if not self.red_side and not self.blue_side:
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
        await asyncio.sleep(SIDE_SELECTION_TIME)
        await self.on_timeout()

    async def check_sides(self, interaction: Union[discord.Interaction, discord.Message]):
        if self.red_side and self.blue_side:
            await update_match_defense(
                match_id=self.match_id,
                defense_start="red" if self.red_side == "defense" else "blue"
            )
            
            match = await get_match(self.match_id)

            score_view = ScoreSubmissionView(self.match_id, self.red_team, self.blue_team)
            
            if isinstance(interaction, discord.Message):
                await score_view.update_message(interaction)
            else:
                await score_view.update_message(interaction.message)

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
        self.score_submission_enabled = False
        self.timeout_task = None
        self.start_time = time.time()
        self.last_submission_time = 0
        self.message = None
        self.admin_called = False
        self.admin_called_by: Optional[str] = None
        self.admin_called_at: Optional[int] = None

    @discord.ui.button(label="Submit Red Team Score", style=discord.ButtonStyle.danger)
    async def submit_red_score(self, interaction: discord.Interaction, button: discord.ui.Button):
        current_time = time.time()
        if current_time - self.last_submission_time < 5:
            await interaction.response.send_message("Please wait 5 seconds between submissions!", ephemeral=True)
            return
        self.last_submission_time = current_time

        if not self.score_submission_enabled:
            elapsed_time = current_time - self.start_time
            remaining_time = 300 - elapsed_time
            if remaining_time > 0:
                minutes = int(remaining_time // 60)
                seconds = int(remaining_time % 60)
                await interaction.response.send_message(f"Score submission will be enabled in {minutes}:{seconds:02d}", ephemeral=True)
                return

        if str(interaction.user.id) != self.red_captain:
            await interaction.response.send_message("Only the Red Team captain can submit the score!", ephemeral=True)
            return

        if self.red_score is not None:
            await interaction.response.send_message("Red Team score has already been submitted!", ephemeral=True)
            return

        modal = ScoreModal("Red Team Score", self, "red")
        await interaction.response.send_modal(modal)
        button.disabled = True
        if self.message:
            await self.message.edit(view=self)

    @discord.ui.button(label="Submit Blue Team Score", style=discord.ButtonStyle.primary)
    async def submit_blue_score(self, interaction: discord.Interaction, button: discord.ui.Button):
        current_time = time.time()
        if current_time - self.last_submission_time < 5:
            await interaction.response.send_message("Please wait 5 seconds between submissions!", ephemeral=True)
            return
        self.last_submission_time = current_time

        if not self.score_submission_enabled:
            elapsed_time = current_time - self.start_time
            remaining_time = 300 - elapsed_time
            if remaining_time > 0:
                minutes = int(remaining_time // 60)
                seconds = int(remaining_time % 60)
                await interaction.response.send_message(f"Score submission will be enabled in {minutes}:{seconds:02d}", ephemeral=True)
                return

        if str(interaction.user.id) != self.blue_captain:
            await interaction.response.send_message("Only the Blue Team captain can submit the score!", ephemeral=True)
            return

        if self.blue_score is not None:
            await interaction.response.send_message("Blue Team score has already been submitted!", ephemeral=True)
            return

        modal = ScoreModal("Blue Team Score", self, "blue")
        await interaction.response.send_modal(modal)
        button.disabled = True
        if self.message:
            await self.message.edit(view=self)

    @discord.ui.button(label="Call Admin", style=discord.ButtonStyle.danger, emoji="⚠️")
    async def call_admin(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.admin_called:
            await interaction.response.send_message("Admin has already been called for this match!", ephemeral=True)
            return

        admin_cog = interaction.client.get_cog("AdminCog")
        if not admin_cog or not admin_cog.admin_channel_id:
            await interaction.response.send_message("Admin channel not set up!", ephemeral=True)
            return

        embed = discord.Embed(
            title="⚠️ Admin Assistance Requested",
            description=f"Match ID: {self.match_id}",
            color=discord.Color.red()
        )
        embed.timestamp = datetime.utcnow()
        embed.add_field(
            name="Teams",
            value=(
                f"🔴 Red Team: {', '.join([f'<@{id}>' for id in self.red_team])}\n"
                f"🔵 Blue Team: {', '.join([f'<@{id}>' for id in self.blue_team])}"
            ),
            inline=False
        )
        embed.add_field(
            name="Scores",
            value=(
                f"🔴 Red Team: {f'{self.red_score[0]}-{self.red_score[1]}' if self.red_score else 'Not submitted'}\n"
                f"🔵 Blue Team: {f'{self.blue_score[0]}-{self.blue_score[1]}' if self.blue_score else 'Not submitted'}"
            ),
            inline=False
        )
        embed.add_field(
            name="Requested by",
            value=f"<@{interaction.user.id}>",
            inline=False
        )

        message = await admin_cog.send_admin_report(self.match_id, interaction.channel_id, embed)
        if message:
            self.admin_called = True
            self.admin_called_by = str(interaction.user.id)
            self.admin_called_at = int(time.time())
            if self.message:
                button.disabled = True
                await self.message.edit(view=self)
            await interaction.response.send_message(
                f"⚠️ Admin has been called by <@{interaction.user.id}>.",
                ephemeral=False
            )
        else:
            await interaction.response.send_message("Failed to send admin report!", ephemeral=True)

    async def update_message(self, message: discord.Message):
        self.message = message
        
        current_time = time.time()
        if not self.score_submission_enabled and (current_time - self.start_time) >= 300:
            self.score_submission_enabled = True
        
        embed = discord.Embed(
            title="Score Submission",
            description="Captains, please submit the match score:",
            color=discord.Color.dark_theme()
        )
        
        red_points_win, blue_points_win, red_points_lose, blue_points_lose, red_avg, blue_avg = await self.get_mmr_points_with_averages()
        
        red_team_value = f"• Captain: <@{self.red_team[0]}>\n"
        red_team_value += "\n".join([f"• <@{id}>" for id in self.red_team[1:]])
        red_team_value += f"\n• Average MMR: **{red_avg:.0f}**"
        red_team_value += f"\n• Points: **+{red_points_win}** (win) / **{red_points_lose}** (lose)"
        
        blue_team_value = f"• Captain: <@{self.blue_team[0]}>\n"
        blue_team_value += "\n".join([f"• <@{id}>" for id in self.blue_team[1:]])
        blue_team_value += f"\n• Average MMR: **{blue_avg:.0f}**"
        blue_team_value += f"\n• Points: **+{blue_points_win}** (win) / **{blue_points_lose}** (lose)"
        
        embed.add_field(
            name="🔴 Red Team",
            value=red_team_value,
            inline=True
        )
        embed.add_field(
            name="🔵 Blue Team",
            value=blue_team_value,
            inline=True
        )
        
        if not self.score_submission_enabled:
            cooldown_end_time = int(self.start_time + 300)
            
            embed.add_field(
                name="⏱️ Score Submission Cooldown",
                value=f"Score submission enabled <t:{cooldown_end_time}:R>",
                inline=False
            )
        else:
            embed.add_field(
                name="Status",
                value="✅ Score submission is now enabled!",
                inline=False
            )

        if self.admin_called:
            embed.add_field(
                name="⚠️ Admin Status",
                value=(
                    f"An admin has been called to review this match\n"
                    f"Called by: <@{self.admin_called_by}> at <t:{self.admin_called_at}:F>"
                ),
                inline=False
            )

        view = discord.ui.View()
        
        red_button = discord.ui.Button(
            label="Submit Red Team Score",
            style=discord.ButtonStyle.danger,
            emoji="🔴",
            disabled=self.red_score is not None or not self.score_submission_enabled
        )
        blue_button = discord.ui.Button(
            label="Submit Blue Team Score",
            style=discord.ButtonStyle.primary,
            emoji="🔵",
            disabled=self.blue_score is not None or not self.score_submission_enabled
        )
        admin_button = discord.ui.Button(
            label="Call Admin",
            style=discord.ButtonStyle.danger,
            emoji="⚠️",
            disabled=self.admin_called
        )
        
        red_button.callback = self.submit_red_score
        blue_button.callback = self.submit_blue_score
        admin_button.callback = self.call_admin
        
        view.add_item(red_button)
        view.add_item(blue_button)
        view.add_item(admin_button)
        
        await message.edit(embed=embed, view=view)
    
    async def get_mmr_points_with_averages(self):
        try:
            match = await get_match(self.match_id)
            leaderboard = await get_leaderboard(match.rank_group)
            current_entries = {str(p.discord_id): p for p in leaderboard.players}
            
            red_team_points = []
            blue_team_points = []
            
            for player_id in self.red_team:
                if player_id in current_entries:
                    red_team_points.append(current_entries[player_id].points)
                else:
                    red_team_points.append(1000)
                    
            for player_id in self.blue_team:
                if player_id in current_entries:
                    blue_team_points.append(current_entries[player_id].points)
                else:
                    blue_team_points.append(1000)
            
            red_avg = sum(red_team_points) / len(red_team_points)
            blue_avg = sum(blue_team_points) / len(blue_team_points)
            
            red_wins_points = calculate_mmr_points(red_avg, blue_avg, True)
            blue_wins_points = calculate_mmr_points(red_avg, blue_avg, False)
            
            return red_wins_points[0], blue_wins_points[1], blue_wins_points[0], red_wins_points[1], red_avg, blue_avg
        except Exception:
            return 25, 25, -25, -25, 1000, 1000

    def validate_score(self, score: int) -> bool:
        return 0 <= score <= 13

    async def update_leaderboard_points(self, interaction: discord.Interaction, winner: str):
        match = await get_match(self.match_id)
        rank_group = match.rank_group

        leaderboard = await get_leaderboard(rank_group)
        current_entries = {str(p.discord_id): p for p in leaderboard.players}
        updated_entries = []

        all_match_players = self.red_team + self.blue_team
        player_ranks = {}
        for player_id in all_match_players:
            player = await get_player(player_id)
            if player and player.rank:
                player_ranks[player_id] = player.rank

        red_team_points = []
        blue_team_points = []
        
        for player_id in self.red_team:
            if player_id in current_entries:
                red_team_points.append(current_entries[player_id].points)
            else:
                red_team_points.append(1000) 
                
        for player_id in self.blue_team:
            if player_id in current_entries:
                blue_team_points.append(current_entries[player_id].points)
            else:
                blue_team_points.append(1000) 
        
        red_avg = sum(red_team_points) / len(red_team_points)
        blue_avg = sum(blue_team_points) / len(blue_team_points)
        
        red_won = winner == "red"
        red_points_change, blue_points_change = calculate_mmr_points(red_avg, blue_avg, red_won)

        for player_id in self.red_team:
            if player_id in current_entries:
                entry = current_entries[player_id]
                entry.points = max(0, entry.points + red_points_change)
                entry.matches_played += 1
                if red_won:
                    entry.winrate = (entry.winrate * (entry.matches_played - 1) + 100) / entry.matches_played
                    entry.streak = max(0, entry.streak) + 1
                else:
                    entry.winrate = (entry.winrate * (entry.matches_played - 1)) / entry.matches_played
                    entry.streak = min(0, entry.streak) - 1
            else:
                new_points = 1000 + red_points_change
                entry = LeaderboardEntry(
                    discord_id=player_id,
                    rank=player_ranks.get(player_id, "Unranked"),
                    points=max(0, new_points),
                    matches_played=1,
                    winrate=100.0 if red_won else 0.0,
                    streak=1 if red_won else -1
                )
            updated_entries.append(entry)

        for player_id in self.blue_team:
            if player_id in current_entries:
                entry = current_entries[player_id]
                entry.points = max(0, entry.points + blue_points_change)
                entry.matches_played += 1
                if not red_won: 
                    entry.winrate = (entry.winrate * (entry.matches_played - 1) + 100) / entry.matches_played
                    entry.streak = max(0, entry.streak) + 1
                else:
                    entry.winrate = (entry.winrate * (entry.matches_played - 1)) / entry.matches_played
                    entry.streak = min(0, entry.streak) - 1
            else:
                new_points = 1000 + blue_points_change
                entry = LeaderboardEntry(
                    discord_id=player_id,
                    rank=player_ranks.get(player_id, "Unranked"),
                    points=max(0, new_points),
                    matches_played=1,
                    winrate=100.0 if not red_won else 0.0,
                    streak=1 if not red_won else -1
                )
            updated_entries.append(entry)

        await update_leaderboard(rank_group, updated_entries)

        history_cog = interaction.client.get_cog("HistoryCog")
        if history_cog:
            await history_cog.add_match_to_history(match)

        leaderboard_cog = interaction.client.get_cog("LeaderboardCog")
        if leaderboard_cog:
            await leaderboard_cog.update_leaderboard()

    async def check_scores(self, interaction: discord.Interaction):
        if self.red_score is not None and self.blue_score is not None:
            if not self.validate_score(self.red_score[0]) or not self.validate_score(self.red_score[1]) or \
               not self.validate_score(self.blue_score[0]) or not self.validate_score(self.blue_score[1]):
                embed = discord.Embed(
                    title="Invalid Score",
                    description="Scores must be between 0 and 13.",
                    color=discord.Color.red()
                )
                await interaction.channel.send(embed=embed)
                self.red_score = None
                self.blue_score = None
                return

            if self.red_score != self.blue_score:
                admin_cog = interaction.client.get_cog("AdminCog")
                if admin_cog and admin_cog.admin_channel_id:
                    embed = discord.Embed(
                        title="⚠️ Score Discrepancy Detected",
                        description=f"Match ID: {self.match_id}",
                        color=discord.Color.red()
                    )
                    embed.add_field(
                        name="Red Team Captain",
                        value=f"<@{self.red_captain}> submitted: {self.red_score[0]}-{self.red_score[1]}",
                        inline=False
                    )
                    embed.add_field(
                        name="Blue Team Captain",
                        value=f"<@{self.blue_captain}> submitted: {self.blue_score[0]}-{self.blue_score[1]}",
                        inline=False
                    )
                    embed.add_field(
                        name="Teams",
                        value=f"🔴 Red: {', '.join([f'<@{id}>' for id in self.red_team])}\n🔵 Blue: {', '.join([f'<@{id}>' for id in self.blue_team])}",
                        inline=False
                    )
                    await admin_cog.send_admin_report(self.match_id, interaction.channel_id, embed)

                embed = discord.Embed(
                    title="⚠️ Score Discrepancy",
                    color=discord.Color.gold(),
                    description=(
                        f"🔴 Red Team Captain <@{self.red_captain}> submitted: {self.red_score[0]}-{self.red_score[1]}\n"
                        f"🔵 Blue Team Captain <@{self.blue_captain}> submitted: {self.blue_score[0]}-{self.blue_score[1]}\n\n"
                        "Please verify the correct score."
                    )
                )
                await interaction.channel.send(embed=embed)
            else:
                red_score = self.red_score[0]
                blue_score = self.red_score[1]
                winner = "red" if red_score > blue_score else "blue"
                
                await update_match_result(
                    match_id=self.match_id,
                    red_score=red_score,
                    blue_score=blue_score,
                    result=winner
                )

                await self.update_leaderboard_points(interaction, winner)

                embed = discord.Embed(
                    title="Match Complete!",
                    color=discord.Color.green(),
                    description=(
                        "**Final Score**\n"
                        f"🔴 Red Team: {red_score}\n"
                        f"🔵 Blue Team: {blue_score}\n\n"
                        f"**{winner.upper()} TEAM WINS!**"
                    )
                )
                await interaction.channel.send(embed=embed)
                
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
            min_length=1,
            max_length=2
        )
        self.opponent_score = discord.ui.TextInput(
            label="Opponent's score",
            placeholder="Enter opponent's rounds won (0-13)",
            required=True,
            min_length=1,
            max_length=2
        )
        self.add_item(self.team_score)
        self.add_item(self.opponent_score)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            team_score = int(self.team_score.value)
            opponent_score = int(self.opponent_score.value)
            
            if not self.view.validate_score(team_score) or not self.view.validate_score(opponent_score):
                embed = discord.Embed(
                    title="Invalid Score",
                    description="Scores must be between 0 and 13.",
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed)
                return

            if self.team == "red":
                self.view.red_score = (team_score, opponent_score)
            else:
                self.view.blue_score = (opponent_score, team_score)

            team_name = "🔴 Red Team" if self.team == "red" else "🔵 Blue Team"
            embed = discord.Embed(
                title="Score Submitted",
                description=f"{team_name} Captain <@{interaction.user.id}> submitted score: {team_score}-{opponent_score}",
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=embed)
            
            await self.view.check_scores(interaction)
        except ValueError:
            embed = discord.Embed(
                title="Invalid Input",
                description="Please enter valid numbers!",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed)

async def create_match(guild: discord.Guild, rank_group: str, players: List[QueueEntry], bot=None):
    match_id = await get_next_match_id()
    
    matches_parent_category = discord.utils.get(guild.categories, name="Matches")
    if not matches_parent_category:
        matches_parent_category = await guild.create_category("Matches")
    
    position = matches_parent_category.position + 1
    match_category = await guild.create_category(match_id, position=position)

    match_channel = await match_category.create_text_channel(name="match")

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(connect=False),
        guild.me: discord.PermissionOverwrite(connect=True, manage_channels=True),
    }
    for player in players:
        try:
            member = guild.get_member(int(player.discord_id))
            if member:
                overwrites[member] = discord.PermissionOverwrite(connect=True)
        except (ValueError, TypeError):
            print(f"Could not get member for ID: {player.discord_id}")

    match_vc = await match_category.create_voice_channel(
        name="Lobby",
        user_limit=10,
        overwrites=overwrites
    )
    
    temp_captains = [players[0].discord_id, players[1].discord_id]
    lobby_master = temp_captains[0]
    
    await create_match_db(
        match_id=match_id,
        players_red=[],
        players_blue=[],
        captain_red=temp_captains[0],
        captain_blue=temp_captains[1],
        lobby_master=lobby_master,
        rank_group=rank_group
    )
    
    match_cog = bot.get_cog("MatchCog") if bot else None
    afk_view = AFKCheckView(match_id, players, rank_group, match_vc, match_cog)
    
    player_pings = " ".join([f"<@{p.discord_id}>" for p in players])
    
    embed = discord.Embed(
        title="🎤 Match Found",
        description=f"{player_pings}\n\n",
        color=discord.Color.dark_theme()
    )

    initial_message = await match_channel.send(embed=embed, view=afk_view)
    afk_view.message = initial_message
    
    await asyncio.sleep(3)
    await afk_view.update_afk_message()

class MatchCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_matches = {}
        self.afk_checks = {}

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if not self.afk_checks:
            return
            
        for match_id, afk_view in list(self.afk_checks.items()):
            if afk_view.check_complete:
                continue
                
            player_ids = {p.discord_id for p in afk_view.players}
            if str(member.id) in player_ids:
                joined_lobby = after.channel == afk_view.lobby_vc
                left_lobby = before.channel == afk_view.lobby_vc and after.channel != afk_view.lobby_vc
                
                if joined_lobby or left_lobby:
                    try:
                        await afk_view.update_afk_message()
                    except Exception as e:
                        print(f"Error updating AFK message: {e}")

async def setup(bot):
    await bot.add_cog(MatchCog(bot))