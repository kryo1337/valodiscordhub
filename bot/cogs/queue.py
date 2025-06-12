import discord
from discord.ext import commands, tasks
from discord import app_commands
from datetime import datetime, timedelta, timezone
import os
from dotenv import load_dotenv
from db.models.queue import QueueEntry, Queue
from utils.db import (
    get_player,
    add_to_queue,
    get_queue,
    remove_player_from_queue,
    create_player,
    update_queue,
    is_player_banned,
    is_player_timeout,
)
from utils.rate_limit import rate_limiter
from .match import create_match

load_dotenv()
GUILD_ID = int(os.getenv("DISCORD_GUILD_ID", "0"))

class QueueView(discord.ui.View):
    def __init__(self, rank_group: str):
        super().__init__(timeout=None)
        self.rank_group = rank_group

    async def update_queue_display(self, channel: discord.TextChannel, queue: Queue):
        try:
            async for message in channel.history(limit=1):
                rank_group_colors = {
                    "iron-plat": discord.Color.blue(),
                    "dia-asc": discord.Color.green(),
                    "imm-radiant": discord.Color.red()
                }
                
                embed = discord.Embed(
                    title=f"{self.rank_group.upper()} Queue",
                    color=rank_group_colors[self.rank_group]
                )
                
                progress = min(len(queue.players) * 10, 100)
                progress_bar = "▰" * (progress // 10) + "▱" * ((100 - progress) // 10)
                embed.add_field(
                    name="Queue Status",
                    value=f"`{progress_bar}` {len(queue.players)}/10",
                    inline=False
                )
                
                if queue.players:
                    players_list = "\n".join([f"• <@{p.discord_id}>" for p in queue.players])
                    embed.add_field(
                        name="Players",
                        value=players_list,
                        inline=False
                    )
                else:
                    embed.add_field(
                        name="Players",
                        value="Queue is empty",
                        inline=False
                    )
                
                embed.set_footer(text="Click the button below to join/leave the queue")
                
                await message.edit(embed=embed, view=self)
                break
        except Exception as e:
            print(f"Error updating queue display: {str(e)}")

    @discord.ui.button(
        label="Queue",
        style=discord.ButtonStyle.grey,
        custom_id="join_button",
    )
    async def join_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        current_time = datetime.now(timezone.utc)
        user_id = str(interaction.user.id)
        matched_players = []
        
        is_limited, remaining = rate_limiter.is_rate_limited(user_id, "queue")
        if is_limited:
            await interaction.response.send_message(
                f"Please wait {remaining} seconds before joining/leaving the queue again!",
                ephemeral=True
            )
            return

        try:
            player = get_player(user_id)
            if not player:
                await interaction.response.send_message(
                    "You need to register first using `/rank` command!", ephemeral=True
                )
                return

            if is_player_banned(user_id):
                await interaction.response.send_message(
                    "You are banned from the queue system!", ephemeral=True
                )
                return

            if is_player_timeout(user_id):
                await interaction.response.send_message(
                    "You are in timeout and cannot join the queue!", ephemeral=True
                )
                return

            rate_limiter.update_cooldown(user_id, "queue")

            queue = get_queue(self.rank_group)
            player_in_queue = any(p.discord_id == user_id for p in queue.players)

            if player_in_queue:
                try:
                    queue = remove_player_from_queue(self.rank_group, user_id)
                    await interaction.response.send_message(
                        "You have left the queue!", ephemeral=True
                    )
                except ValueError as e:
                    await interaction.response.send_message(
                        f"❌ {str(e)}",
                        ephemeral=True
                    )
                    return
                except Exception as e:
                    print(f"Error leaving queue: {str(e)}")
                    await interaction.response.send_message(
                        f"An error occurred while leaving the queue: {str(e)}",
                        ephemeral=True
                    )
                    return
            else:
                try:
                    queue = add_to_queue(self.rank_group, user_id)
                    await interaction.response.send_message(
                        "You have joined the queue!", ephemeral=True
                    )
                except ValueError as e:
                    await interaction.response.send_message(
                        f"❌ {str(e)}",
                        ephemeral=True
                    )
                    return
                except Exception as e:
                    print(f"Error joining queue: {str(e)}")
                    await interaction.response.send_message(
                        f"An error occurred while joining the queue: {str(e)}",
                        ephemeral=True
                    )
                    return

            if len(queue.players) >= 10:
                matched_players = queue.players[:10]
                for player in matched_players:
                    try:
                        queue = remove_player_from_queue(self.rank_group, player.discord_id)
                    except Exception as e:
                        print(f"Error removing matched player from queue: {str(e)}")

            queue = get_queue(self.rank_group)
            await self.update_queue_display(interaction.channel, queue)

            if matched_players:
                await create_match(interaction.guild, self.rank_group, matched_players)

        except Exception as e:
            print(f"Error in queue button: {str(e)}")
            await interaction.response.send_message(
                f"An error occurred: {str(e)}",
                ephemeral=True
            )

class QueueCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.add_listener(self.on_ready)
        self.check_queue_timeout.start()

    async def on_ready(self):
        await self.setup_existing_queues()

    @tasks.loop(minutes=5)
    async def check_queue_timeout(self):
        current_time = datetime.now(timezone.utc)
        rank_groups = ["iron-plat", "dia-asc", "imm-radiant"]
        
        for rank_group in rank_groups:
            try:
                queue = get_queue(rank_group)
                if not queue:
                    continue

                players_to_remove = []
                for player in queue.players:
                    time_in_queue = current_time - player.joined_at
                    if time_in_queue > timedelta(hours=2):
                        players_to_remove.append(player.discord_id)

                if players_to_remove:
                    for discord_id in players_to_remove:
                        queue = remove_player_from_queue(rank_group, discord_id)
                    
                    guild = self.bot.get_guild(GUILD_ID)
                    if guild:
                        category = discord.utils.get(guild.categories, name="valohub")
                        if category:
                            channel = discord.utils.get(category.channels, name=f"queue-{rank_group}")
                            if channel:
                                async for message in channel.history(limit=1):
                                    rank_group_colors = {
                                        "iron-plat": discord.Color.blue(),
                                        "dia-asc": discord.Color.green(),
                                        "imm-radiant": discord.Color.red()
                                    }
                                    
                                    embed = discord.Embed(
                                        title=f"{rank_group.upper()} Queue",
                                        color=rank_group_colors[rank_group]
                                    )
                                    
                                    progress = min(len(queue.players) * 10, 100)
                                    progress_bar = "▰" * (progress // 10) + "▱" * ((100 - progress) // 10)
                                    embed.add_field(
                                        name="Queue Status",
                                        value=f"`{progress_bar}` {len(queue.players)}/10",
                                        inline=False
                                    )
                                    
                                    if queue.players:
                                        players_list = "\n".join([f"• <@{p.discord_id}>" for p in queue.players])
                                        embed.add_field(
                                            name="Players",
                                            value=players_list,
                                            inline=False
                                        )
                                    else:
                                        embed.add_field(
                                            name="Players",
                                            value="Queue is empty",
                                            inline=False
                                        )
                                    
                                    embed.set_footer(text="Click the button below to join/leave the queue")
                                    
                                    await message.edit(embed=embed, view=QueueView(rank_group))
                                    break
            except Exception as e:
                print(f"Error checking queue timeout for {rank_group}: {str(e)}")

    @check_queue_timeout.before_loop
    async def before_check_queue_timeout(self):
        await self.bot.wait_until_ready()

    async def setup_existing_queues(self):
        guild = self.bot.get_guild(GUILD_ID)
        if not guild:
            return

        category = discord.utils.get(guild.categories, name="valohub")
        if not category:
            return

        rank_groups = ["iron-plat", "dia-asc", "imm-radiant"]
        for rank_group in rank_groups:
            channel = discord.utils.get(category.channels, name=f"queue-{rank_group}")
            if channel:
                async for message in channel.history(limit=None):
                    try:
                        await message.delete()
                    except discord.NotFound:
                        pass
                
                queue = get_queue(rank_group) or Queue(rank_group=rank_group, players=[])
                view = QueueView(rank_group)
                
                rank_group_colors = {
                    "iron-plat": discord.Color.blue(),
                    "dia-asc": discord.Color.green(),
                    "imm-radiant": discord.Color.red()
                }
                
                embed = discord.Embed(
                    title=f"{rank_group.upper()} Queue",
                    color=rank_group_colors[rank_group]
                )
                
                progress = min(len(queue.players) * 10, 100)
                progress_bar = "▰" * (progress // 10) + "▱" * ((100 - progress) // 10)
                embed.add_field(
                    name="Queue Status",
                    value=f"`{progress_bar}` {len(queue.players)}/10",
                    inline=False
                )
                
                if queue.players:
                    players_list = "\n".join([f"• <@{p.discord_id}>" for p in queue.players])
                    embed.add_field(
                        name="Players",
                        value=players_list,
                        inline=False
                    )
                else:
                    embed.add_field(
                        name="Players",
                        value="Queue is empty",
                        inline=False
                    )
                
                embed.set_footer(text="Click the button below to join/leave the queue")
                
                await channel.send(embed=embed, view=view)

    @app_commands.command(name="test_queue")
    @app_commands.default_permissions(administrator=True)
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    @app_commands.describe(count="Number of test players to add to queue")
    async def test_queue(self, interaction: discord.Interaction, count: int = 9):
        await interaction.response.defer(ephemeral=True)

        if count < 1 or count > 10:
            await interaction.followup.send("❌ Count must be between 1 and 10", ephemeral=True)
            return

        category = discord.utils.get(interaction.guild.categories, name="valohub")
        if not category:
            await interaction.followup.send(
                "❌ valohub category not found. Run /setup_queue first.", ephemeral=True
            )
            return

        channel = discord.utils.get(category.channels, name="queue-imm-radiant")
        if not channel:
            await interaction.followup.send(
                "❌ Queue channel not found. Run /setup_queue first.", ephemeral=True
            )
            return

        test_players = []
        for i in range(count):
            discord_id = f"test_user_{i}"
            riot_id = f"TestUser{i}"
            rank = "Immortal 3"

            player = get_player(discord_id)
            if not player:
                player = create_player(discord_id, riot_id, rank)

            queue_entry = QueueEntry(
                discord_id=player.discord_id
            )
            test_players.append(queue_entry)

        queue = get_queue("imm-radiant")
        if not queue:
            queue = Queue(rank_group="imm-radiant", players=[])

        queue.players.extend(test_players)
        update_queue("imm-radiant", queue.players)

        async for message in channel.history(limit=1):
            rank_group_colors = {
                "iron-plat": discord.Color.blue(),
                "dia-asc": discord.Color.green(),
                "imm-radiant": discord.Color.red()
            }
            
            embed = discord.Embed(
                title="IMMORTAL-RADIANT Queue",
                color=rank_group_colors["imm-radiant"]
            )
            
            progress = min(len(queue.players) * 10, 100)
            progress_bar = "▰" * (progress // 10) + "▱" * ((100 - progress) // 10)
            embed.add_field(
                name="Queue Status",
                value=f"`{progress_bar}` {len(queue.players)}/10",
                inline=False
            )
            
            if queue.players:
                players_list = "\n".join([f"• <@{p.discord_id}>" for p in queue.players])
                embed.add_field(
                    name="Players",
                    value=players_list,
                    inline=False
                )
            
            embed.set_footer(text="Click the button below to join/leave the queue")
            
            await message.edit(embed=embed, view=QueueView("imm-radiant"))
            break

        await interaction.followup.send(
            f"✅ Added {count} test players to the queue!", ephemeral=True
        )

    @app_commands.command(name="setup_queue")
    @app_commands.default_permissions(administrator=True)
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def setup_queue(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        category = discord.utils.get(interaction.guild.categories, name="valohub")
        if category:
            for channel in category.channels:
                if channel.name.startswith("queue-"):
                    await channel.delete()
        else:
            category = await interaction.guild.create_category("valohub")

        rank_groups = ["iron-plat", "dia-asc", "imm-radiant"]
        for rank_group in rank_groups:
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

            role = discord.utils.get(interaction.guild.roles, name=rank_group)
            if role:
                overwrites[role] = discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=False
                )

            channel = await category.create_text_channel(
                name=f"queue-{rank_group}", overwrites=overwrites
            )

            queue = get_queue(rank_group) or Queue(rank_group=rank_group, players=[])
            view = QueueView(rank_group)
            
            rank_group_colors = {
                "iron-plat": discord.Color.blue(),
                "dia-asc": discord.Color.green(),
                "imm-radiant": discord.Color.red()
            }
            
            embed = discord.Embed(
                title=f"{rank_group.upper()} Queue",
                color=rank_group_colors[rank_group]
            )
            
            progress = min(len(queue.players) * 10, 100)
            progress_bar = "▰" * (progress // 10) + "▱" * ((100 - progress) // 10)
            embed.add_field(
                name="Queue Status",
                value=f"`{progress_bar}` {len(queue.players)}/10",
                inline=False
            )
            
            if queue.players:
                players_list = "\n".join([f"• <@{p.discord_id}>" for p in queue.players])
                embed.add_field(
                    name="Players",
                    value=players_list,
                    inline=False
                )
            else:
                embed.add_field(
                    name="Players",
                    value="Queue is empty",
                    inline=False
                )
            
            embed.set_footer(text="Click the button below to join/leave the queue")
            
            await channel.send(embed=embed, view=view)

        await interaction.followup.send(
            "✅ Queue channels have been set up!", ephemeral=True
        )

    async def remove_player_from_all_queues(self, guild: discord.Guild, discord_id: str):
        rank_groups = ["iron-plat", "dia-asc", "imm-radiant"]
        for rank_group in rank_groups:
            try:
                queue = get_queue(rank_group)
                if queue and any(p.discord_id == discord_id for p in queue.players):
                    queue = remove_player_from_queue(rank_group, discord_id)
                    category = discord.utils.get(guild.categories, name="valohub")
                    if category:
                        channel = discord.utils.get(category.channels, name=f"queue-{rank_group}")
                        if channel:
                            await self.update_queue_display(channel, queue)
            except Exception as e:
                print(f"Error removing player from queue {rank_group}: {e}")

    async def update_queue_display(self, channel: discord.TextChannel, queue: Queue):
        try:
            async for message in channel.history(limit=1):
                rank_group_colors = {
                    "iron-plat": discord.Color.blue(),
                    "dia-asc": discord.Color.green(),
                    "imm-radiant": discord.Color.red()
                }
                
                embed = discord.Embed(
                    title=f"{queue.rank_group.upper()} Queue",
                    color=rank_group_colors[queue.rank_group]
                )
                
                progress = min(len(queue.players) * 10, 100)
                progress_bar = "▰" * (progress // 10) + "▱" * ((100 - progress) // 10)
                embed.add_field(
                    name="Queue Status",
                    value=f"`{progress_bar}` {len(queue.players)}/10",
                    inline=False
                )
                
                if queue.players:
                    players_list = "\n".join([f"• <@{p.discord_id}>" for p in queue.players])
                    embed.add_field(
                        name="Players",
                        value=players_list,
                        inline=False
                    )
                else:
                    embed.add_field(
                        name="Players",
                        value="Queue is empty",
                        inline=False
                    )
                
                embed.set_footer(text="Click the button below to join/leave the queue")
                
                await message.edit(embed=embed, view=QueueView(queue.rank_group))
                break
        except Exception as e:
            print(f"Error updating queue display: {str(e)}")

async def setup(bot):
    cog = QueueCog(bot)
    await bot.add_cog(cog)