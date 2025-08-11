"""
Cleaning Roster Commands
Discord slash commands for managing cleaning rosters
"""

import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional, Literal
from ..cleaning.cleaning_manager import cleaning_manager
from ..utils.logging import get_logger

logger = get_logger(__name__)


class CleaningCommands(commands.Cog):
    """Commands for managing cleaning rosters"""
    
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="create_roster", description="Create a new cleaning roster")
    async def create_roster(self, interaction: discord.Interaction, name: str):
        """Create a new cleaning roster"""
        try:
            result = await cleaning_manager.create_roster(
                roster_name=name,
                creator_id=str(interaction.user.id),
                guild_id=str(interaction.guild_id)
            )
            
            if result["success"]:
                # Create private channel for the roster
                guild = interaction.guild
                category = None
                
                # Try to find or create a "Cleaning" category
                for cat in guild.categories:
                    if cat.name.lower() == "cleaning":
                        category = cat
                        break
                
                if not category:
                    category = await guild.create_category("Cleaning")
                
                # Create private channel
                overwrites = {
                    guild.default_role: discord.PermissionOverwrite(read_messages=False),
                    interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True)
                }
                
                channel_name = f"cleaning-{name.lower().replace(' ', '-')}"
                channel = await guild.create_text_channel(
                    channel_name,
                    category=category,
                    overwrites=overwrites,
                    topic=f"Private cleaning roster channel for {name}"
                )
                
                # Update roster with channel ID
                await cleaning_manager.set_channel(name, str(channel.id), str(interaction.guild_id))
                
                embed = discord.Embed(
                    title="🧹 Cleaning Roster Created",
                    description=f"**{name}** roster has been created with private channel {channel.mention}",
                    color=0x00ff00
                )
                embed.add_field(
                    name="Next Steps",
                    value="• Use `/add_member` to add people to the roster\n• Use `/add_task` to add cleaning tasks\n• Tasks reset weekly on Monday",
                    inline=False
                )
                
            else:
                embed = discord.Embed(
                    title="❌ Error",
                    description=result["message"],
                    color=0xff0000
                )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error creating roster: {e}")
            await interaction.response.send_message("❌ An error occurred while creating the roster.", ephemeral=True)

    @app_commands.command(name="add_member", description="Add a member to a cleaning roster")
    async def add_member(self, interaction: discord.Interaction, roster: str, user: discord.Member):
        """Add a member to a cleaning roster"""
        try:
            result = await cleaning_manager.add_member(
                roster_name=roster,
                user_id=str(user.id),
                guild_id=str(interaction.guild_id)
            )
            
            if result["success"]:
                # Add user to the roster's private channel
                roster_info = await cleaning_manager.get_roster_info(roster, str(interaction.guild_id))
                if roster_info and roster_info["channel_id"]:
                    channel = self.bot.get_channel(int(roster_info["channel_id"]))
                    if channel:
                        await channel.set_permissions(user, read_messages=True, send_messages=True)
                
                embed = discord.Embed(
                    title="✅ Member Added",
                    description=f"{user.mention} has been added to **{roster}**",
                    color=0x00ff00
                )
                embed.add_field(
                    name="Roster Info",
                    value=f"Total members: {result['member_count']}",
                    inline=False
                )
            else:
                embed = discord.Embed(
                    title="❌ Error",
                    description=result["message"],
                    color=0xff0000
                )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error adding member: {e}")
            await interaction.response.send_message("❌ An error occurred while adding the member.", ephemeral=True)

    @app_commands.command(name="add_task", description="Add a cleaning task to a roster")
    async def add_task(self, interaction: discord.Interaction, roster: str, task_name: str, 
                      category: Literal["personal", "household"], points: app_commands.Range[int, 1, 10]):
        """Add a cleaning task to a roster"""
        try:
            result = await cleaning_manager.add_task(
                roster_name=roster,
                guild_id=str(interaction.guild_id),
                task_name=task_name,
                category=category,
                points=points,
                user_id=str(interaction.user.id)
            )
            
            if result["success"]:
                embed = discord.Embed(
                    title="📋 Task Added",
                    description=result["message"],
                    color=0x00ff00
                )
                embed.add_field(
                    name="Task Details",
                    value=f"**Category:** {category.title()}\n**Points:** {points}\n**Total {category} tasks:** {result['task_count']}",
                    inline=False
                )
            else:
                embed = discord.Embed(
                    title="❌ Error",
                    description=result["message"],
                    color=0xff0000
                )
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"Error adding task: {e}")
            await interaction.response.send_message("❌ An error occurred while adding the task.", ephemeral=True)

    @app_commands.command(name="complete_task", description="Mark a cleaning task as completed")
    async def complete_task(self, interaction: discord.Interaction, roster: str, task_name: str, 
                          category: Literal["personal", "household"]):
        """Mark a cleaning task as completed"""
        try:
            result = await cleaning_manager.complete_task(
                roster_name=roster,
                guild_id=str(interaction.guild_id),
                task_name=task_name,
                category=category,
                user_id=str(interaction.user.id)
            )
            
            if result["success"]:
                embed = discord.Embed(
                    title="✅ Task Completed!",
                    description=result["message"],
                    color=0x00ff00
                )
                
                # Check if user has completed 4+ points this week
                weekly_points = result["weekly_points"]
                lifetime_points = result["lifetime_points"]
                if weekly_points >= 4:
                    embed.add_field(
                        name="🎉 Weekly Goal Achieved!",
                        value=f"You've completed {weekly_points} points this week! Great job!\nLifetime total: {lifetime_points} points",
                        inline=False
                    )
                else:
                    remaining = 4 - weekly_points
                    embed.add_field(
                        name="📊 Progress",
                        value=f"Weekly points: {weekly_points}/4 ({remaining} points remaining)\nLifetime total: {lifetime_points} points",
                        inline=False
                    )
            else:
                embed = discord.Embed(
                    title="❌ Error",
                    description=result["message"],
                    color=0xff0000
                )
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"Error completing task: {e}")
            await interaction.response.send_message("❌ An error occurred while completing the task.", ephemeral=True)

    @app_commands.command(name="list_tasks", description="List remaining cleaning tasks for this week")
    async def list_tasks(self, interaction: discord.Interaction, roster: str):
        """List remaining cleaning tasks for this week"""
        try:
            remaining_tasks = await cleaning_manager.get_remaining_tasks(roster, str(interaction.guild_id))
            
            if not remaining_tasks:
                embed = discord.Embed(
                    title="❌ Error",
                    description=f"Roster **{roster}** not found",
                    color=0xff0000
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            embed = discord.Embed(
                title=f"📋 Remaining Tasks - {roster}",
                description=f"Tasks remaining for this week ({remaining_tasks['total_remaining']} total)",
                color=0x0099ff
            )
            
            # Personal tasks
            personal_tasks = remaining_tasks["personal"]
            if personal_tasks:
                personal_text = "\n".join([f"• **{task['name']}** ({task['points']} pts)" for task in personal_tasks])
                embed.add_field(
                    name=f"👤 Personal Tasks ({len(personal_tasks)})",
                    value=personal_text[:1024],  # Discord field limit
                    inline=False
                )
            
            # Household tasks
            household_tasks = remaining_tasks["household"]
            if household_tasks:
                household_text = "\n".join([f"• **{task['name']}** ({task['points']} pts)" for task in household_tasks])
                embed.add_field(
                    name=f"🏠 Household Tasks ({len(household_tasks)})",
                    value=household_text[:1024],  # Discord field limit
                    inline=False
                )
            
            if not personal_tasks and not household_tasks:
                embed.add_field(
                    name="🎉 All Done!",
                    value="No tasks remaining for this week!",
                    inline=False
                )
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"Error listing tasks: {e}")
            await interaction.response.send_message("❌ An error occurred while listing tasks.", ephemeral=True)

    @app_commands.command(name="completed_tasks", description="List completed cleaning tasks for this week")
    async def completed_tasks(self, interaction: discord.Interaction, roster: str):
        """List completed cleaning tasks for this week"""
        try:
            completed_tasks = await cleaning_manager.get_completed_tasks(roster, str(interaction.guild_id))
            
            if completed_tasks is None:
                embed = discord.Embed(
                    title="❌ Error",
                    description=f"Roster **{roster}** not found",
                    color=0xff0000
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            embed = discord.Embed(
                title=f"✅ Completed Tasks - {roster}",
                description=f"Tasks completed this week ({len(completed_tasks)} total)",
                color=0x00ff00
            )
            
            if completed_tasks:
                # Group by user
                user_tasks = {}
                for task in completed_tasks:
                    user_id = task["completed_by"]
                    if user_id not in user_tasks:
                        user_tasks[user_id] = []
                    user_tasks[user_id].append(task)
                
                for user_id, tasks in user_tasks.items():
                    user = self.bot.get_user(int(user_id))
                    user_name = user.display_name if user else f"User {user_id}"
                    
                    total_points = sum(task["points"] for task in tasks)
                    task_list = "\n".join([f"• **{task['name']}** ({task['category']}, {task['points']} pts)" 
                                         for task in tasks])
                    
                    embed.add_field(
                        name=f"{user_name} - {total_points} points",
                        value=task_list[:1024],  # Discord field limit
                        inline=False
                    )
            else:
                embed.add_field(
                    name="No completed tasks",
                    value="No tasks have been completed this week yet.",
                    inline=False
                )
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"Error listing completed tasks: {e}")
            await interaction.response.send_message("❌ An error occurred while listing completed tasks.", ephemeral=True)

    @app_commands.command(name="points", description="Show current week's points for all roster members")
    async def points(self, interaction: discord.Interaction, roster: str):
        """Show current week's points for all roster members"""
        try:
            user_points = await cleaning_manager.get_user_points(roster, str(interaction.guild_id))
            
            if user_points is None:
                embed = discord.Embed(
                    title="❌ Error",
                    description=f"Roster **{roster}** not found",
                    color=0xff0000
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            embed = discord.Embed(
                title=f"📊 Weekly Points - {roster}",
                description="Points earned this week (Goal: 4 points per person)",
                color=0x0099ff
            )
            
            if user_points:
                # Sort users by points (highest first)
                sorted_users = sorted(user_points.items(), key=lambda x: x[1], reverse=True)
                
                points_text = ""
                for user_id, points in sorted_users:
                    user = self.bot.get_user(int(user_id))
                    user_name = user.display_name if user else f"User {user_id}"
                    
                    # Add emoji based on goal achievement
                    if points >= 4:
                        emoji = "🏆"
                    elif points >= 2:
                        emoji = "🔥"
                    elif points >= 1:
                        emoji = "⭐"
                    else:
                        emoji = "📋"
                    
                    points_text += f"{emoji} **{user_name}**: {points}/4 points\n"
                
                embed.add_field(
                    name="Member Points",
                    value=points_text,
                    inline=False
                )
            else:
                embed.add_field(
                    name="No points yet",
                    value="No one has completed any tasks this week.",
                    inline=False
                )
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"Error showing points: {e}")
            await interaction.response.send_message("❌ An error occurred while showing points.", ephemeral=True)

    @app_commands.command(name="lifetime_points", description="Show lifetime points for all roster members")
    async def lifetime_points(self, interaction: discord.Interaction, roster: str):
        """Show lifetime points for all roster members"""
        try:
            lifetime_points = await cleaning_manager.get_lifetime_points(roster, str(interaction.guild_id))
            
            if lifetime_points is None:
                embed = discord.Embed(
                    title="❌ Error",
                    description=f"Roster **{roster}** not found",
                    color=0xff0000
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            embed = discord.Embed(
                title=f"🏆 Lifetime Points - {roster}",
                description="All-time points earned by roster members",
                color=0xffd700  # Gold color
            )
            
            if lifetime_points:
                # Sort users by lifetime points (highest first)
                sorted_users = sorted(lifetime_points.items(), key=lambda x: x[1], reverse=True)
                
                points_text = ""
                for rank, (user_id, points) in enumerate(sorted_users, 1):
                    user = self.bot.get_user(int(user_id))
                    user_name = user.display_name if user else f"User {user_id}"
                    
                    # Add rank emoji for top 3
                    if rank == 1:
                        emoji = "🥇"
                    elif rank == 2:
                        emoji = "🥈"
                    elif rank == 3:
                        emoji = "🥉"
                    else:
                        emoji = f"{rank}."
                    
                    points_text += f"{emoji} **{user_name}**: {points} points\n"
                
                embed.add_field(
                    name="Leaderboard",
                    value=points_text,
                    inline=False
                )
            else:
                embed.add_field(
                    name="No points yet",
                    value="No one has earned any points yet.",
                    inline=False
                )
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"Error showing lifetime points: {e}")
            await interaction.response.send_message("❌ An error occurred while showing lifetime points.", ephemeral=True)

    @app_commands.command(name="roster_info", description="Show information about a cleaning roster")
    async def roster_info(self, interaction: discord.Interaction, roster: str):
        """Show information about a cleaning roster"""
        try:
            roster_info = await cleaning_manager.get_roster_info(roster, str(interaction.guild_id))
            
            if not roster_info:
                embed = discord.Embed(
                    title="❌ Error",
                    description=f"Roster **{roster}** not found",
                    color=0xff0000
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            embed = discord.Embed(
                title=f"🧹 Roster Info - {roster_info['name']}",
                color=0x0099ff
            )
            
            # Get member names
            member_names = []
            for member_id in roster_info["members"]:
                user = self.bot.get_user(int(member_id))
                member_names.append(user.display_name if user else f"User {member_id}")
            
            embed.add_field(
                name="👥 Members",
                value="\n".join([f"• {name}" for name in member_names]),
                inline=True
            )
            
            # Task counts
            personal_count = len(roster_info["base_tasks"]["personal"])
            household_count = len(roster_info["base_tasks"]["household"])
            
            embed.add_field(
                name="📋 Tasks",
                value=f"Personal: {personal_count}\nHousehold: {household_count}",
                inline=True
            )
            
            # Channel info
            if roster_info["channel_id"]:
                channel = self.bot.get_channel(int(roster_info["channel_id"]))
                channel_mention = channel.mention if channel else "Channel not found"
            else:
                channel_mention = "No channel set"
            
            embed.add_field(
                name="💬 Channel",
                value=channel_mention,
                inline=True
            )
            
            # Weekly progress
            current_week_data = roster_info["weekly_data"][roster_info["current_week"]]
            remaining_total = (len(current_week_data["remaining_tasks"]["personal"]) + 
                             len(current_week_data["remaining_tasks"]["household"]))
            completed_total = len(current_week_data["completed_tasks"])
            
            embed.add_field(
                name="📊 This Week",
                value=f"Remaining: {remaining_total}\nCompleted: {completed_total}",
                inline=True
            )
            
            embed.set_footer(text=f"Created by User {roster_info['creator_id']}")
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"Error showing roster info: {e}")
            await interaction.response.send_message("❌ An error occurred while showing roster info.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(CleaningCommands(bot))