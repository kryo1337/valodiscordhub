import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
import os

from utils.scraper import get_player_rank
from utils.db import get_player, create_player, update_player_rank

load_dotenv()
GUILD_ID = int(os.getenv("DISCORD_GUILD_ID", "0"))

RANK_GROUPS = {
    "iron-plat": ["Iron", "Bronze", "Silver", "Gold", "Platinum"],
    "dia-asc": ["Diamond", "Ascendant"],
    "imm1-radiant": ["Immortal", "Radiant"],
}


class Rank(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def is_valid_rank(self, rank: str) -> bool:
        return "error" not in rank.lower()

    def get_role_name_from_rank(self, rank: str) -> str:
        base_rank = rank.split()[0]
        for role_name, ranks in RANK_GROUPS.items():
            if base_rank in [r.capitalize() for r in ranks]:
                return role_name
        return None

    async def assign_role(self, member: discord.Member, role_name: str):
        guild = member.guild
        role = discord.utils.get(guild.roles, name=role_name)

        if not role:
            try:
                role = await guild.create_role(
                    name=role_name, reason="Auto-created for rank grouping"
                )
            except discord.Forbidden:
                return False

        try:
            current_rank_roles = [
                r for r in member.roles if r.name in RANK_GROUPS.keys()
            ]
            if current_rank_roles:
                await member.remove_roles(*current_rank_roles)
            await member.add_roles(role)
            return True
        except discord.Forbidden:
            return False

    @app_commands.command(name="rank", description="check rank")
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def rank(self, interaction: discord.Interaction, riot_id: str):
        await interaction.response.defer()

        try:
            rank = await get_player_rank(riot_id)

            if not self.is_valid_rank(rank):
                await interaction.followup.send(
                    f"❌ Failed to fetch rank for **{riot_id}**. Please try again later or check if the Riot ID is valid."
                )
                return

            member = interaction.user
            player = get_player(str(interaction.user.id))
            role_assigned = False

            if not player:
                player = create_player(
                    discord_id=str(interaction.user.id), riot_id=riot_id, rank=rank
                )
                role_name = self.get_role_name_from_rank(rank)
                if role_name:
                    role_assigned = await self.assign_role(member, role_name)

                await interaction.followup.send(
                    f"**{riot_id}** has rank: **{rank}**\n"
                    f"✅ Player profile created!"
                    + (f"\n✅ Assigned role: **{role_name}**" if role_assigned else "")
                )
            else:
                if player.riot_id != riot_id:
                    await interaction.followup.send(
                        f"❌ This Riot ID is different from your registered one.\n"
                        f"Your registered Riot ID: **{player.riot_id}**"
                    )
                    return

                player = update_player_rank(str(interaction.user.id), rank)
                role_name = self.get_role_name_from_rank(rank)
                if role_name:
                    role_assigned = await self.assign_role(member, role_name)

                await interaction.followup.send(
                    f"**{riot_id}** has rank: **{rank}**\n"
                    f"✅ Rank updated!"
                    + (f"\n✅ Assigned role: **{role_name}**" if role_assigned else "")
                )

        except Exception as e:
            await interaction.followup.send(f"❌ Error: {str(e)}")


async def setup(bot: commands.Bot):
    await bot.add_cog(Rank(bot))
