import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
import os

from utils.scraper import get_player_rank
from utils.db import get_player, create_player, update_player_rank
from utils.rate_limit import rate_limiter
from utils.permissions import check_player_status

load_dotenv()
GUILD_ID = int(os.getenv("DISCORD_GUILD_ID", "0"))

RANK_GROUPS = {
    "iron-plat": ["Iron", "Bronze", "Silver", "Gold", "Platinum"],
    "dia-asc": ["Diamond", "Ascendant"],
    "imm-radiant": ["Immortal", "Radiant"],
}

VALID_RANKS = [
    "Iron 1", "Iron 2", "Iron 3",
    "Bronze 1", "Bronze 2", "Bronze 3",
    "Silver 1", "Silver 2", "Silver 3",
    "Gold 1", "Gold 2", "Gold 3",
    "Platinum 1", "Platinum 2", "Platinum 3",
    "Diamond 1", "Diamond 2", "Diamond 3",
    "Ascendant 1", "Ascendant 2", "Ascendant 3",
    "Immortal 1", "Immortal 2", "Immortal 3",
    "Radiant"
]

class RankModal(discord.ui.Modal, title="Enter your Riot ID"):
    riot_id = discord.ui.TextInput(
        label="Riot ID",
        placeholder="Enter your Riot ID (e.g. Player#EU1)",
        required=True,
        min_length=3,
        max_length=20
    )

    async def on_submit(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        
        is_limited, remaining = rate_limiter.is_rate_limited(user_id, "rank")
        if is_limited:
            await interaction.response.send_message(
                f"Please wait {remaining} seconds before updating your rank again!",
                ephemeral=True
            )
            return

        allowed, reason = check_player_status(user_id)
        if not allowed:
            await interaction.response.send_message(reason, ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        try:
            rank = await get_player_rank(self.riot_id.value)
            if not rank or "error" in rank.lower():
                player = get_player(str(interaction.user.id))
                if not player:
                    player = create_player(
                        discord_id=str(interaction.user.id),
                        riot_id=self.riot_id.value,
                        rank=None
                    )
                    await interaction.followup.send(
                        f"✅ Player profile created!\n"
                        f"❌ Could not fetch your rank. Make sure your Riot ID is correct and your profile is public.",
                        ephemeral=True
                    )
                else:
                    await interaction.followup.send(
                        f"❌ Could not fetch your rank. Make sure your Riot ID is correct and your profile is public.\n"
                        f"Your registered Riot ID: **{player.riot_id}**",
                        ephemeral=True
                    )
                return

            rate_limiter.update_cooldown(user_id, "rank")

            member = interaction.user
            player = get_player(str(interaction.user.id))
            role_assigned = False

            if not player:
                player = create_player(
                    discord_id=str(interaction.user.id),
                    riot_id=self.riot_id.value,
                    rank=rank
                )
                role_name = self.get_role_name_from_rank(rank)
                if role_name:
                    role_assigned = await self.assign_role(member, role_name)

                await interaction.followup.send(
                    f"**{self.riot_id.value}** has rank: **{rank}**\n"
                    f"✅ Player profile created!"
                    + (f"\n✅ Assigned role: **{role_name}**" if role_assigned else ""),
                    ephemeral=True
                )
            else:
                if player.riot_id != self.riot_id.value:
                    await interaction.followup.send(
                        f"❌ This Riot ID is different from your registered one.\n"
                        f"Your registered Riot ID: **{player.riot_id}**",
                        ephemeral=True
                    )
                    return

                player = update_player_rank(str(interaction.user.id), rank)
                role_name = self.get_role_name_from_rank(rank)
                if role_name:
                    role_assigned = await self.assign_role(member, role_name)

                await interaction.followup.send(
                    f"**{self.riot_id.value}** has rank: **{rank}**\n"
                    f"✅ Rank updated!"
                    + (f"\n✅ Assigned role: **{role_name}**" if role_assigned else ""),
                    ephemeral=True
                )

        except Exception as e:
            await interaction.followup.send(f"❌ Error: {str(e)}", ephemeral=True)

    def is_valid_rank(self, rank: str) -> bool:
        if not rank:
            return False
        rank = rank.strip()
        if "error" in rank.lower():
            return False
        return rank in VALID_RANKS

    def get_role_name_from_rank(self, rank: str) -> str:
        if not rank:
            return None
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

class RankButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Get Rank Role",
            style=discord.ButtonStyle.primary,
            emoji="🎮"
        )

    async def callback(self, interaction: discord.Interaction):
        modal = RankModal()
        await interaction.response.send_modal(modal)

class RankView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(RankButton())

class Rank(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.bot.add_listener(self.on_ready)

    async def on_ready(self):
        await self.setup_existing_rank_channel()

    async def setup_existing_rank_channel(self):
        guild = self.bot.get_guild(GUILD_ID)
        if not guild:
            return

        category = discord.utils.get(guild.categories, name="valohub")
        if not category:
            return

        channel = discord.utils.get(category.channels, name="rank")
        if channel:
            async for message in channel.history(limit=None):
                try:
                    await message.delete()
                except discord.NotFound:
                    pass

            embed = discord.Embed(
                title="Valorant Rank Setup",
                description="Get your rank role by clicking the button below and entering your Riot ID!",
                color=discord.Color.blue()
            )

            embed.add_field(
                name="📝 How to use",
                value="1. Click the button below\n"
                      "2. Enter your Riot ID (e.g. Player#EU1)\n"
                      "3. The bot will fetch your rank and assign you the appropriate role",
                inline=False
            )

            embed.add_field(
                name="🎯 Rank Groups",
                value="• Iron - Platinum: `iron-plat`\n"
                      "• Diamond - Ascendant: `dia-asc`\n"
                      "• Immortal - Radiant: `imm-radiant`",
                inline=False
            )

            embed.add_field(
                name="⚠️ Important",
                value="• Make sure your Riot ID is correct\n"
                      "• The bot will update your rank role automatically\n"
                      "• You can update your rank anytime using the same button",
                inline=False
            )

            embed.set_footer(text="Need help? Contact an admin!")

            view = RankView()
            await channel.send(embed=embed, view=view)

    @app_commands.command(name="setup_rank")
    @app_commands.default_permissions(administrator=True)
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def setup_rank(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        try:
            category = discord.utils.get(interaction.guild.categories, name="valohub")
            if category:
                existing_channel = discord.utils.get(category.channels, name="rank")
                if existing_channel:
                    await existing_channel.delete()
            else:
                category = await interaction.guild.create_category("valohub")

            overwrites = {
                interaction.guild.default_role: discord.PermissionOverwrite(
                    view_channel=False,
                    send_messages=False
                ),
                interaction.guild.me: discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    manage_channels=True
                ),
            }

            for role_name in ["iron-plat", "dia-asc", "imm-radiant"]:
                role = discord.utils.get(interaction.guild.roles, name=role_name)
                if role:
                    overwrites[role] = discord.PermissionOverwrite(
                        view_channel=True,
                        send_messages=False
                    )

            channel = await interaction.guild.create_text_channel(
                name="rank",
                category=category,
                topic="Get your Valorant rank here!",
                overwrites=overwrites,
                reason="Auto-created for rank setup"
            )

            embed = discord.Embed(
                title="Valorant Rank Setup",
                description="Get your rank role by clicking the button below and entering your Riot ID!",
                color=discord.Color.blue()
            )

            embed.add_field(
                name="📝 How to use",
                value="1. Click the button below\n"
                      "2. Enter your Riot ID (e.g. Player#EU1)\n"
                      "3. The bot will fetch your rank and assign you the appropriate role",
                inline=False
            )

            embed.add_field(
                name="🎯 Rank Groups",
                value="• Iron - Platinum: `iron-plat`\n"
                      "• Diamond - Ascendant: `dia-asc`\n"
                      "• Immortal - Radiant: `imm-radiant`",
                inline=False
            )

            embed.add_field(
                name="⚠️ Important",
                value="• Make sure your Riot ID is correct\n"
                      "• The bot will update your rank role automatically\n"
                      "• You can update your rank anytime using the same button",
                inline=False
            )

            embed.set_footer(text="Need help? Contact an admin!")

            view = RankView()
            await channel.send(embed=embed, view=view)

            await interaction.followup.send(
                f"✅ Rank channel setup complete! Check {channel.mention}",
                ephemeral=True
            )

        except Exception as e:
            await interaction.followup.send(
                f"❌ Failed to setup rank channel: {str(e)}",
                ephemeral=True
            )

async def setup(bot: commands.Bot):
    await bot.add_cog(Rank(bot))
