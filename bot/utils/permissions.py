from typing import Optional
import discord
from discord.ext import commands
from utils.db import is_player_banned, is_player_timeout

def check_admin(interaction: discord.Interaction) -> bool:
    return interaction.user.guild_permissions.administrator

def check_rank_group(interaction: discord.Interaction, required_rank_group: str) -> bool:
    return any(role.name == required_rank_group for role in interaction.user.roles)

def check_player_status(user_id: str) -> tuple[bool, Optional[str]]:
    if is_player_banned(user_id):
        return False, "You are banned from using this command."
    if is_player_timeout(user_id):
        return False, "You are currently in timeout."
    return True, None

def check_command_permissions(interaction: discord.Interaction, command_name: str) -> tuple[bool, Optional[str]]:
    if command_name in ["setup_admin", "setup_queue", "setup_rank", "setup_leaderboard", 
                       "setup_history", "setup_stats", "ban", "unban", "timeout", 
                       "set_rank", "set_points", "refresh_all"]:
        if not check_admin(interaction):
            return False, "This command requires administrator permissions."
        return True, None

    if command_name == "queue":
        allowed, reason = check_player_status(str(interaction.user.id))
        if not allowed:
            return False, reason
        return True, None

    if command_name == "rank":
        allowed, reason = check_player_status(str(interaction.user.id))
        if not allowed:
            return False, reason
        return True, None

    if command_name in ["stats", "history"]:
        return True, None

    return True, None 