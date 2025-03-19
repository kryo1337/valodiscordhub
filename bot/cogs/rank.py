import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
import os

from utils.scraper import get_player_rank

load_dotenv()
GUILD_ID = int(os.getenv("DISCORD_GUILD_ID", "0"))


class Rank(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="rank", description="check rank")
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def rank(self, interaction: discord.Interaction, riot_id: str):
        await interaction.response.defer()

        try:
            rank = await get_player_rank(riot_id)
            await interaction.followup.send(f"**{riot_id}** has rank: **{rank}**")
        except Exception as e:
            await interaction.followup.send(f"error: {e}")


async def setup(bot: commands.Bot):
    await bot.add_cog(Rank(bot))
