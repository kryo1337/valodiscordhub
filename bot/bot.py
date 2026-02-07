import os
import asyncio
import aiohttp
import discord
import logging
from discord.ext import commands
from discord import app_commands
from pathlib import Path
from dotenv import load_dotenv
from typing import cast
from utils.rate_limit import rate_limiter
from utils.permissions import check_command_permissions

# Load .env from project root
load_dotenv(Path(__file__).resolve().parent.parent / ".env")
token = os.getenv("DISCORD_TOKEN")
if token is None:
    raise ValueError("DISCORD_TOKEN not set in environment.")
TOKEN: str = cast(str, token)

BOT_PREFIX = "!"


def setup_logger():
    logging.getLogger().setLevel(logging.WARNING)

    logger = logging.getLogger("valohub")
    logger.setLevel(logging.INFO)

    logger.handlers = []

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    )
    logger.addHandler(console_handler)

    return logger


logger = setup_logger()

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix=BOT_PREFIX, intents=intents)

guild_id_str = os.getenv("DISCORD_GUILD_ID")
GUILD_ID = int(guild_id_str) if guild_id_str else None


@bot.event
async def on_app_command_error(
    interaction: discord.Interaction, error: app_commands.AppCommandError
):
    if isinstance(error, app_commands.CommandOnCooldown):
        await interaction.response.send_message(
            f"This command is on cooldown. Try again in {error.retry_after:.2f}s",
            ephemeral=True,
        )
    elif isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message(
            "You don't have permission to use this command.", ephemeral=True
        )
    else:
        logger.error(f"Command error: {str(error)}")
        await interaction.response.send_message(
            f"An error occurred: {str(error)}", ephemeral=True
        )


@bot.before_invoke
async def before_command(ctx):
    is_limited, remaining = rate_limiter.is_rate_limited(
        str(ctx.author.id), ctx.command.name
    )
    if is_limited:
        raise commands.CommandOnCooldown(ctx.command, remaining)

    allowed, reason = check_command_permissions(ctx, ctx.command.name)
    if not allowed:
        raise commands.MissingPermissions([reason])

    rate_limiter.update_cooldown(str(ctx.author.id), ctx.command.name)


async def load_extensions():
    for filename in os.listdir("./cogs"):
        if not filename.endswith(".py"):
            continue
        extension_name = f"cogs.{filename[:-3]}"
        if extension_name in bot.extensions:
            try:
                await bot.reload_extension(extension_name)
            except Exception:
                try:
                    await bot.unload_extension(extension_name)
                except Exception:
                    pass
                await bot.load_extension(extension_name)
        else:
            await bot.load_extension(extension_name)


@bot.event
async def on_ready():
    logger.info(f"Logged in as {bot.user.name}")
    try:
        if GUILD_ID:
            guild = discord.Object(id=GUILD_ID)
            synced = await bot.tree.sync(guild=guild)
            logger.info(f"Synced {len(synced)} slash command(s) for guild {GUILD_ID}.")
        else:
            synced = await bot.tree.sync()
            logger.info(f"Synced {len(synced)} global slash command(s).")
    except Exception as e:
        logger.error(f"Failed to sync slash commands: {e}")


async def main():
    backoff_seconds = 5
    while True:
        try:
            async with bot:
                await load_extensions()
                await bot.start(TOKEN)
        except (aiohttp.ClientConnectorError, aiohttp.ClientConnectorDNSError) as e:
            logger.error(f"Discord connect failed: {e}; retrying in {backoff_seconds}s")
        except Exception as e:
            logger.error(f"Bot crashed: {e}; retrying in {backoff_seconds}s")
        await asyncio.sleep(backoff_seconds)
        backoff_seconds = min(backoff_seconds * 2, 300)


if __name__ == "__main__":
    asyncio.run(main())
