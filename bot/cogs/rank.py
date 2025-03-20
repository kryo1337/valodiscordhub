import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
import os

from utils.scraper import get_player_rank
from utils.db import get_player, create_player, update_player_rank

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
            
            player = get_player(str(interaction.user.id))
            if not player:
                player = create_player(
                    discord_id=str(interaction.user.id),
                    riot_id=riot_id,
                    rank=rank
                )
                await interaction.followup.send(
                    f"**{riot_id}** has rank: **{rank}**\n"
                    f"✅ Player profile created!"
                )
            else:
                if player.riot_id != riot_id:
                    await interaction.followup.send(
                        f"❌ This Riot ID is different from your registered one.\n"
                        f"Your registered Riot ID: **{player.riot_id}**"
                    )
                    return
                
                player = update_player_rank(str(interaction.user.id), rank)
                await interaction.followup.send(
                    f"**{riot_id}** has rank: **{rank}**\n"
                    f"✅ Rank updated!"
                )
                
        except Exception as e:
            await interaction.followup.send(f"❌ Error: {str(e)}")


async def setup(bot: commands.Bot):
    await bot.add_cog(Rank(bot))
