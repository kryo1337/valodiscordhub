import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
import os
from typing import Optional

from utils.scraper import get_player_rank
from utils.db import get_player, create_player, update_player_rank
from utils.rate_limit import rate_limiter
from utils.permissions import check_player_status

load_dotenv()
GUILD_ID = int(os.getenv("DISCORD_GUILD_ID"))

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
        placeholder="Enter your Riot ID (e.g. Player#1337)",
        required=True,
        min_length=3,
        max_length=20
    )

    def __init__(self):
        super().__init__()

    async def on_submit(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        
        is_limited, remaining = rate_limiter.is_rate_limited(user_id, "rank")
        if is_limited:
            await interaction.response.send_message(
                f"Please wait {remaining} seconds before submitting another rank request!",
                ephemeral=True
            )
            return

        allowed, reason = await check_player_status(user_id)
        if not allowed:
            await interaction.response.send_message(reason, ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        try:
            riot_id = self.riot_id.value.strip()
            
            guild = interaction.guild
            category = discord.utils.get(guild.categories, name="valohub")
            if category:
                admin_ranks_channel = discord.utils.get(category.channels, name="admin-ranks")
                if admin_ranks_channel:
                    async for message in admin_ranks_channel.history(limit=50):
                        if (message.author == interaction.client.user and 
                            message.embeds and 
                            message.embeds[0].footer and 
                            message.embeds[0].footer.text == f"Ticket ID: {user_id}"):
                            await interaction.followup.send(
                                f"❌ You already have a pending rank ticket in {admin_ranks_channel.mention}\n"
                                f"Please wait for an admin to review your request.",
                                ephemeral=True
                            )
                            return

            rank_cog = interaction.client.get_cog("Rank")
            if rank_cog:
                ticket_channel = await rank_cog.create_rank_ticket(interaction.guild, interaction.user, riot_id)
            else:
                ticket_channel = None
            
            if ticket_channel:
                rate_limiter.update_cooldown(user_id, "rank")
                
                await interaction.followup.send(
                    f"✅ Rank verification request submitted!",
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    "❌ Failed to create rank ticket. Please try again later.",
                    ephemeral=True
                )

        except Exception as e:
            await interaction.followup.send(f"❌ Error: {str(e)}", ephemeral=True)

class RankTicketView(discord.ui.View):
    def __init__(self, user: discord.Member, riot_id: str):
        super().__init__(timeout=None)
        self.user = user
        self.riot_id = riot_id

    @discord.ui.button(label="Select Rank", style=discord.ButtonStyle.success, emoji="✅", custom_id="select_rank")
    async def select_rank(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("You don't have permission to approve rank requests!", ephemeral=True)
            return

        view = RankSelectionView(self.user, self.riot_id, interaction.message)
        await interaction.response.send_message("Select a rank:", view=view, ephemeral=True)

    @discord.ui.button(label="Reject Request", style=discord.ButtonStyle.danger, emoji="❌", custom_id="reject_request")
    async def reject_request(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("You don't have permission to reject rank requests!", ephemeral=True)
            return

        modal = RejectionModal(self.user, self.riot_id, interaction.message)
        await interaction.response.send_modal(modal)

class RankSelectionModal(discord.ui.Modal, title="Select Rank"):
    rank = discord.ui.TextInput(
        label="Rank",
        placeholder="Enter rank",
        required=True,
        min_length=2,
        max_length=20
    )

    def __init__(self, user: discord.Member, riot_id: str, message: discord.Message):
        super().__init__()
        self.user = user
        self.riot_id = riot_id
        self.message = message

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        rank = self.rank.value.strip()
        if rank not in VALID_RANKS:
            await interaction.followup.send(
                f"❌ Invalid rank: {rank}\nValid ranks: {', '.join(VALID_RANKS)}",
                ephemeral=True
            )
            return

        try:
            player = await get_player(str(self.user.id))
            if not player:
                player = await create_player(
                    discord_id=str(self.user.id),
                    riot_id=self.riot_id,
                    rank=rank
                )
            else:
                player = await update_player_rank(str(self.user.id), rank)

            role_name = self.get_role_name_from_rank(rank)
            role_assigned = False
            if role_name:
                role_assigned = await self.assign_role(self.user, role_name)

            success_embed = discord.Embed(
                title="✅ Rank Approved",
                description=f"**User:** {self.user.mention}\n**Riot ID:** {self.riot_id}\n**Rank:** {rank}",
                color=discord.Color.green()
            )
            if role_assigned:
                success_embed.add_field(name="Role Assigned", value=f"✅ {role_name}", inline=False)

            try:
                user_embed = discord.Embed(
                    title="🎮 Rank Approved!",
                    description=f"Your rank has been set to **{rank}**",
                    color=discord.Color.green()
                )
                user_embed.add_field(name="Riot ID", value=self.riot_id, inline=False)
                if role_assigned:
                    user_embed.add_field(name="Role", value=f"✅ {role_name}", inline=False)
                
                await self.user.send(embed=user_embed)
            except:
                pass

            try:
                public_embed = discord.Embed(
                    title="✅ Rank Approved",
                    description=(
                        f"**User:** {self.user.mention}\n"
                        f"**Riot ID:** {self.riot_id}\n"
                        f"**Rank:** {rank}"
                    ),
                    color=discord.Color.green()
                )
                if role_assigned:
                    public_embed.add_field(name="Role Assigned", value=f"✅ {role_name}", inline=False)
                public_embed.add_field(name="Assigned By", value=interaction.user.mention, inline=False)

                category = interaction.guild and discord.utils.get(interaction.guild.categories, name="valohub")
                admin_ranks_channel = discord.utils.get(category.channels, name="admin-ranks") if category else None
                target_channel = admin_ranks_channel or (self.message.channel if hasattr(self, "message") else None)
                if target_channel:
                    await target_channel.send(embed=public_embed)
            except Exception:
                pass

            await self.message.delete()

        except Exception as e:
            await interaction.followup.send(f"❌ Error: {str(e)}", ephemeral=True)

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

class RankSelectionView(discord.ui.View):
    def __init__(self, user: discord.Member, riot_id: str, message: discord.Message):
        super().__init__(timeout=300)
        self.user = user
        self.riot_id = riot_id
        self.message = message

    @discord.ui.select(
        placeholder="Select a rank...",
        options=[
            discord.SelectOption(label="Iron 1", value="Iron 1"),
            discord.SelectOption(label="Iron 2", value="Iron 2"),
            discord.SelectOption(label="Iron 3", value="Iron 3"),
            discord.SelectOption(label="Bronze 1", value="Bronze 1"),
            discord.SelectOption(label="Bronze 2", value="Bronze 2"),
            discord.SelectOption(label="Bronze 3", value="Bronze 3"),
            discord.SelectOption(label="Silver 1", value="Silver 1"),
            discord.SelectOption(label="Silver 2", value="Silver 2"),
            discord.SelectOption(label="Silver 3", value="Silver 3"),
            discord.SelectOption(label="Gold 1", value="Gold 1"),
            discord.SelectOption(label="Gold 2", value="Gold 2"),
            discord.SelectOption(label="Gold 3", value="Gold 3"),
            discord.SelectOption(label="Platinum 1", value="Platinum 1"),
            discord.SelectOption(label="Platinum 2", value="Platinum 2"),
            discord.SelectOption(label="Platinum 3", value="Platinum 3"),
            discord.SelectOption(label="Diamond 1", value="Diamond 1"),
            discord.SelectOption(label="Diamond 2", value="Diamond 2"),
            discord.SelectOption(label="Diamond 3", value="Diamond 3"),
            discord.SelectOption(label="Ascendant 1", value="Ascendant 1"),
            discord.SelectOption(label="Ascendant 2", value="Ascendant 2"),
            discord.SelectOption(label="Ascendant 3", value="Ascendant 3"),
            discord.SelectOption(label="Immortal 1", value="Immortal 1"),
            discord.SelectOption(label="Immortal 2", value="Immortal 2"),
            discord.SelectOption(label="Immortal 3", value="Immortal 3"),
            discord.SelectOption(label="Radiant", value="Radiant"),
        ]
    )
    async def select_rank(self, interaction: discord.Interaction, select: discord.ui.Select):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("You don't have permission to approve rank requests!", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        rank = select.values[0]
        
        try:
            player = await get_player(str(self.user.id))
            if not player:
                player = await create_player(
                    discord_id=str(self.user.id),
                    riot_id=self.riot_id,
                    rank=rank
                )
            else:
                player = await update_player_rank(str(self.user.id), rank)

            role_name = self.get_role_name_from_rank(rank)
            role_assigned = False
            if role_name:
                role_assigned = await self.assign_role(self.user, role_name)

            success_embed = discord.Embed(
                title="✅ Rank Approved",
                description=f"**User:** {self.user.mention}\n**Riot ID:** {self.riot_id}\n**Rank:** {rank}",
                color=discord.Color.green()
            )
            if role_assigned:
                success_embed.add_field(name="Role Assigned", value=f"✅ {role_name}", inline=False)

            try:
                user_embed = discord.Embed(
                    title="🎮 Rank Approved!",
                    description=f"Your rank has been set to **{rank}**",
                    color=discord.Color.green()
                )
                user_embed.add_field(name="Riot ID", value=self.riot_id, inline=False)
                if role_assigned:
                    user_embed.add_field(name="Role", value=f"✅ {role_name}", inline=False)
                
                await self.user.send(embed=user_embed)
            except:
                pass

            try:
                public_embed = discord.Embed(
                    title="✅ Rank Approved",
                    description=(
                        f"**User:** {self.user.mention}\n"
                        f"**Riot ID:** {self.riot_id}\n"
                        f"**Rank:** {rank}"
                    ),
                    color=discord.Color.green()
                )
                if role_assigned:
                    public_embed.add_field(name="Role Assigned", value=f"✅ {role_name}", inline=False)
                public_embed.add_field(name="Assigned By", value=interaction.user.mention, inline=False)

                category = interaction.guild and discord.utils.get(interaction.guild.categories, name="valohub")
                admin_ranks_channel = discord.utils.get(category.channels, name="admin-ranks") if category else None
                target_channel = admin_ranks_channel or (self.message.channel if hasattr(self, "message") else None)
                if target_channel:
                    await target_channel.send(embed=public_embed)
            except Exception:
                pass

            await self.message.delete()

        except Exception as e:
            await interaction.followup.send(f"❌ Error: {str(e)}", ephemeral=True)

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

class RejectionModal(discord.ui.Modal, title="Reject Rank Request"):
    reason = discord.ui.TextInput(
        label="Reason for Rejection",
        placeholder="Enter reason",
        required=True,
        min_length=1,
        max_length=500,
        style=discord.TextStyle.paragraph
    )

    def __init__(self, user: discord.Member, riot_id: str, message: discord.Message):
        super().__init__()
        self.user = user
        self.riot_id = riot_id
        self.message = message

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        try:
            try:
                user_embed = discord.Embed(
                    title="❌ Rank Request Rejected",
                    description="Your rank request has been rejected by an admin.",
                    color=discord.Color.red()
                )
                user_embed.add_field(name="Riot ID", value=self.riot_id, inline=False)
                user_embed.add_field(name="Reason", value=self.reason.value, inline=False)
                
                await self.user.send(embed=user_embed)
            except:
                pass

            try:
                public_embed = discord.Embed(
                    title="❌ Rank Request Rejected",
                    description=(
                        f"**User:** {self.user.mention}\n"
                        f"**Riot ID:** {self.riot_id}\n"
                        f"**Reason:** {self.reason.value}"
                    ),
                    color=discord.Color.red()
                )
                public_embed.add_field(name="Rejected By", value=interaction.user.mention, inline=False)
                category = interaction.guild and discord.utils.get(interaction.guild.categories, name="valohub")
                admin_ranks_channel = discord.utils.get(category.channels, name="admin-ranks") if category else None
                target_channel = admin_ranks_channel or (self.message.channel if hasattr(self, "message") else None)
                if target_channel:
                    await target_channel.send(embed=public_embed)
            except Exception:
                pass

            await self.message.delete()

        except Exception as e:
            await interaction.followup.send(f"❌ Error: {str(e)}", ephemeral=True)

class RankButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Request Rank Verification",
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

    async def create_rank_ticket(self, guild: discord.Guild, user: discord.Member, riot_id: str) -> Optional[discord.TextChannel]:
        try:
            category = discord.utils.get(guild.categories, name="valohub")
            if not category:
                category = await guild.create_category("valohub")

            channel = discord.utils.get(category.channels, name="admin-ranks")
            if not channel:
                overwrites = {
                    guild.default_role: discord.PermissionOverwrite(read_messages=False),
                    guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                }
                
                channel = await guild.create_text_channel(
                    name="admin-ranks",
                    category=category,
                    topic="Rank verification requests",
                    overwrites=overwrites
                )

            embed = discord.Embed(
                title="🎮 Rank Verification Request",
                description=f"**User:** {user.mention}\n**Riot ID:** {riot_id}",
                color=discord.Color.blue()
            )
            
            embed.add_field(
                name="🔗 Tracker.gg Profile",
                value=f"[Click here to view profile](https://tracker.gg/valorant/profile/riot/{riot_id.replace('#', '%23')}/overview)",
                inline=False
            )
            
            embed.add_field(
                name="📝 Instructions",
                value="1. Click the tracker link above\n"
                      "2. Verify the user's rank\n"
                      "3. Use the buttons below to approve or reject",
                inline=False
            )

            embed.set_footer(text=f"Ticket ID: {user.id}")

            view = RankTicketView(user, riot_id)
            await channel.send(embed=embed, view=view)

            return channel

        except Exception as e:
            print(f"Error creating rank ticket: {e}")
            return None

    async def setup_existing_rank_channel(self):
        guild = self.bot.get_guild(GUILD_ID)
        if not guild:
            return

        category = discord.utils.get(guild.categories, name="valohub")
        if not category:
            return

        channel = discord.utils.get(category.channels, name="rank")
        if channel:
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=False
                ),
                guild.me: discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    manage_channels=True
                ),
            }
            for role_name in ["iron-plat", "dia-asc", "imm-radiant"]:
                role = discord.utils.get(guild.roles, name=role_name)
                if role:
                    overwrites[role] = discord.PermissionOverwrite(
                        view_channel=True,
                        send_messages=False
                    )
            await channel.edit(overwrites=overwrites)
            async for message in channel.history(limit=None):
                try:
                    await message.delete()
                except discord.NotFound:
                    pass

            embed = discord.Embed(
                title="Valorant Rank Verification",
                description="Request rank verification by clicking the button below!",
                color=discord.Color.blue()
            )

            embed.add_field(
                name="📝 How it works",
                value="1. Click the button below\n"
                      "2. Enter your Riot ID (e.g. Player#1337)\n"
                      "3. A ticket will be created for admin review\n"
                      "4. Admin will verify your rank and assign you the appropriate role",
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
                      "• Your profile must be public on tracker.gg\n"
                      "• You'll receive a DM when your rank is approved",
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
                    view_channel=True,
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
                topic="Request rank verification here!",
                overwrites=overwrites,
                reason="Auto-created for rank verification"
            )

            embed = discord.Embed(
                title="Valorant Rank Verification",
                description="Request rank verification by clicking the button below!",
                color=discord.Color.blue()
            )

            embed.add_field(
                name="📝 How it works",
                value="1. Click the button below\n"
                      "2. Enter your Riot ID (e.g. Player#1337)\n"
                      "3. A ticket will be created for admin review\n"
                      "4. Admin will verify your rank and assign you the appropriate role",
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
                      "• Your profile must be public on tracker.gg\n"
                      "• You'll receive a DM when your rank is approved",
                inline=False
            )

            embed.set_footer(text="Need help? Contact an admin!")

            view = RankView()
            await channel.send(embed=embed, view=view)

            await interaction.followup.send(
                f"✅ Rank verification channel setup complete! Check {channel.mention}",
                ephemeral=True
            )

        except Exception as e:
            await interaction.followup.send(
                f"❌ Failed to setup rank channel: {str(e)}",
                ephemeral=True
            )

async def setup(bot: commands.Bot):
    await bot.add_cog(Rank(bot))
