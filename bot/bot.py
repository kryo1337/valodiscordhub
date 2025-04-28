import os
import asyncio
import discord
from discord.ext import commands
from dotenv import load_dotenv
from typing import cast

load_dotenv()
token = os.getenv("DISCORD_TOKEN")
if token is None:
    raise ValueError("DISCORD_TOKEN not set in environment.")
TOKEN: str = cast(str, token)

BOT_PREFIX = "!"

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix=BOT_PREFIX, intents=intents)

guild_id_str = os.getenv("DISCORD_GUILD_ID")
GUILD_ID = int(guild_id_str) if guild_id_str else None


async def load_extensions():
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py"):
            await bot.load_extension(f"cogs.{filename[:-3]}")


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name}")
    try:
        if GUILD_ID:
            guild = discord.Object(id=GUILD_ID)
            synced = await bot.tree.sync(guild=guild)
            print(f"Synced {len(synced)} slash command(s) for guild {GUILD_ID}.")
        else:
            synced = await bot.tree.sync()
            print(f"Synced {len(synced)} global slash command(s).")
    except Exception as e:
        print("Failed to sync slash commands:", e)


async def main():
    async with bot:
        await load_extensions()
        await bot.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
