"""
Cleaning Roster Commands
Discord commands for managing cleaning rosters
"""

import discord
from discord.ext import commands
from typing import Optional
from ..cleaning.cleaning_manager import cleaning_manager
from ..utils.logging import get_logger

logger = get_logger(__name__)


class CleaningCommands(commands.Cog):
    """Commands for managing cleaning rosters"""
    
    def __init__(self, bot):
        self.bot = bot
        self._executing_commands = set()  # Track executing commands to prevent duplicates

    async def _get_roster_from_context(self, ctx) -> Optional[dict]:
        """Get roster information from channel context"""
        roster_info = await cleaning_manager.get_roster_by_channel(str(ctx.channel.id))
        return roster_info

    @commands.command(name="create_roster")
    async def create_roster(self, ctx, *, name: str):
        """Create a new cleaning roster
        Usage: !create_roster <name>
        Example: !create_roster Main House
        """
        # Prevent duplicate execution
        command_key = f"create_roster_{ctx.author.id}_{name}"
        if command_key in self._executing_commands:
            return
        
        self._executing_commands.add(command_key)
        
        try:
            result = await cleaning_manager.create_roster(
                roster_name=name,
                creator_id=str(ctx.author.id),
                guild_id=str(ctx.guild.id)
            )
            
            if result["success"]:
                # Create private channel for the roster
                guild = ctx.guild
                category = None
                
                # Try to find or create a "Cleaning" category
                for cat in guild.categories:
                    if cat.name.lower() == "cleaning":
                        category = cat
                        break
                
                if not category:
                    category = await guild.create_category("Cleaning")
                
                # Create private channel with bot access
                overwrites = {
                    guild.default_role: discord.PermissionOverwrite(read_messages=False),
                    ctx.author: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                    guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)  # Bot access
                }
                
                channel_name = f"cleaning-{name.lower().replace(' ', '-')}"
                channel = await guild.create_text_channel(
                    channel_name,
                    category=category,
                    overwrites=overwrites,
                    topic=f"Private cleaning roster channel for {name}"
                )
                
                # Update roster with channel ID
                await cleaning_manager.set_channel(name, str(channel.id), str(ctx.guild.id))
                
                embed = discord.Embed(
                    title="🧹 Cleaning Roster Created",
                    description=f"**{name}** roster has been created with private channel {channel.mention}",
                    color=0x00ff00
                )
                embed.add_field(
                    name="Next Steps",
                    value=f"• Go to {channel.mention} to manage your roster\n• Use `!add_member @user` to add people\n• Use `!add_task` to add cleaning tasks\n• Tasks reset weekly on Monday",
                    inline=False
                )
                
            else:
                embed = discord.Embed(
                    title="❌ Error",
                    description=result["message"],
                    color=0xff0000
                )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error creating roster: {e}")
            await ctx.send("❌ An error occurred while creating the roster.")
        finally:
            self._executing_commands.discard(command_key)

    @commands.command(name="add_member")
    async def add_member(self, ctx, user: discord.Member):
        """Add a member to this roster's channel
        Usage: !add_member @user
        Example: !add_member @John
        Must be used in a cleaning roster channel
        """
        # Prevent duplicate execution
        command_key = f"add_member_{ctx.channel.id}_{user.id}"
        if command_key in self._executing_commands:
            return
        
        self._executing_commands.add(command_key)
        
        try:
            # Check if this is a roster channel
            roster_info = await self._get_roster_from_context(ctx)
            if not roster_info:
                await ctx.send("❌ This command must be used in a cleaning roster channel. Use `!create_roster` to create one.")
                return
            
            result = await cleaning_manager.add_member(
                roster_name=roster_info["name"],
                user_id=str(user.id),
                guild_id=str(ctx.guild.id)
            )
            
            if result["success"]:
                # Add user to the current channel
                await ctx.channel.set_permissions(user, read_messages=True, send_messages=True)
                
                embed = discord.Embed(
                    title="✅ Member Added",
                    description=f"{user.mention} has been added to **{roster_info['name']}**",
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
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error adding member: {e}")
            await ctx.send("❌ An error occurred while adding the member.")
        finally:
            self._executing_commands.discard(command_key)

    @commands.command(name="add_task")
    async def add_task(self, ctx, category: str, points: int, *, task_name: str):
        """Add a cleaning task to this roster
        Usage: !add_task <category> <points> <task_name>
        Example: !add_task personal 3 Clean bedroom (one-time task)
        Example: !add_task household 5 Vacuum living room (recurring weekly)
        
        Personal tasks: One-time only, won't refresh next week (unless incomplete)
        Household tasks: Recurring weekly, will refresh every Monday
        
        Category must be 'personal' or 'household'
        Points must be between 1 and 10
        Must be used in a cleaning roster channel
        """
        try:
            # Check if this is a roster channel
            roster_info = await self._get_roster_from_context(ctx)
            if not roster_info:
                await ctx.send("❌ This command must be used in a cleaning roster channel. Use `!create_roster` to create one.")
                return
            
            # Validate category
            if category.lower() not in ["personal", "household"]:
                await ctx.send("❌ Category must be 'personal' or 'household'")
                return
                
            # Validate points
            if not 1 <= points <= 10:
                await ctx.send("❌ Points must be between 1 and 10")
                return
            
            result = await cleaning_manager.add_task(
                roster_name=roster_info["name"],
                guild_id=str(ctx.guild.id),
                task_name=task_name,
                category=category.lower(),
                points=points,
                user_id=str(ctx.author.id)
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
            
            await ctx.send(embed=embed)
            
        except ValueError:
            await ctx.send("❌ Points must be a number between 1 and 10")
        except Exception as e:
            logger.error(f"Error adding task: {e}")
            await ctx.send("❌ An error occurred while adding the task.")

    @commands.command(name="complete_task", aliases=["complete", "done"])
    async def complete_task(self, ctx, task_identifier: str, category: str = None):
        """Mark a cleaning task as completed
        Usage: !complete_task <number> or !complete_task <category> <task_name>
        Examples: 
            !complete_task 1 (completes task #1 from !tasks list)
            !complete_task personal Clean bedroom
            !done 3 (alias for complete_task)
        Must be used in a cleaning roster channel
        """
        try:
            # Check if this is a roster channel
            roster_info = await self._get_roster_from_context(ctx)
            if not roster_info:
                await ctx.send("❌ This command must be used in a cleaning roster channel.")
                return
            
            # Get remaining tasks to create numbered list
            remaining_tasks = await cleaning_manager.get_remaining_tasks(roster_info["name"], str(ctx.guild.id))
            if not remaining_tasks:
                await ctx.send("❌ Could not fetch tasks for this roster.")
                return
            
            # Create numbered task list
            all_tasks = []
            for task in remaining_tasks["personal"]:
                all_tasks.append({"task": task, "category": "personal"})
            for task in remaining_tasks["household"]:
                all_tasks.append({"task": task, "category": "household"})
            
            if not all_tasks:
                await ctx.send("🎉 No tasks remaining! All done for this week!")
                return
            
            # Check if first argument is a number
            try:
                task_number = int(task_identifier)
                if 1 <= task_number <= len(all_tasks):
                    # Complete task by number
                    selected_task = all_tasks[task_number - 1]
                    task_name = selected_task["task"]["name"]
                    task_category = selected_task["category"]
                else:
                    await ctx.send(f"❌ Task number must be between 1 and {len(all_tasks)}. Use `!tasks` to see the numbered list.")
                    return
            except ValueError:
                # First argument is not a number, treat as category
                if category is None:
                    await ctx.send("❌ Usage: `!complete_task <number>` or `!complete_task <category> <task_name>`")
                    return
                
                # Validate category
                if task_identifier.lower() not in ["personal", "household"]:
                    await ctx.send("❌ Category must be 'personal' or 'household'")
                    return
                
                task_category = task_identifier.lower()
                task_name = category  # category parameter is actually task name in this case
            
            result = await cleaning_manager.complete_task(
                roster_name=roster_info["name"],
                guild_id=str(ctx.guild.id),
                task_name=task_name,
                category=task_category,
                user_id=str(ctx.author.id)
            )
            
            if result["success"]:
                embed = discord.Embed(
                    title="✅ Task Completed!",
                    description=result["message"],
                    color=0x00ff00
                )
                
                # Get the dynamic weekly goal
                weekly_goal = await cleaning_manager.get_weekly_goal(roster_info["name"], str(ctx.guild.id))
                
                # Check if user has completed the weekly goal
                weekly_points = result["weekly_points"]
                lifetime_points = result["lifetime_points"]
                if weekly_points >= weekly_goal:
                    embed.add_field(
                        name="🎉 Weekly Goal Achieved!",
                        value=f"You've completed {weekly_points} points this week! Great job!\nLifetime total: {lifetime_points} points",
                        inline=False
                    )
                else:
                    remaining = weekly_goal - weekly_points
                    embed.add_field(
                        name="📊 Progress",
                        value=f"Weekly points: {weekly_points}/{weekly_goal} ({remaining} points remaining)\nLifetime total: {lifetime_points} points",
                        inline=False
                    )
            else:
                embed = discord.Embed(
                    title="❌ Error",
                    description=result["message"],
                    color=0xff0000
                )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error completing task: {e}")
            await ctx.send("❌ An error occurred while completing the task.")

    @commands.command(name="list_tasks", aliases=["tasks"])
    async def list_tasks(self, ctx):
        """List remaining cleaning tasks for this week
        Usage: !list_tasks or !tasks
        Shows numbered tasks that can be completed with !complete_task <number>
        Must be used in a cleaning roster channel
        """
        try:
            # Check if this is a roster channel
            roster_info = await self._get_roster_from_context(ctx)
            if not roster_info:
                await ctx.send("❌ This command must be used in a cleaning roster channel.")
                return
            
            remaining_tasks = await cleaning_manager.get_remaining_tasks(roster_info["name"], str(ctx.guild.id))
            
            if not remaining_tasks:
                embed = discord.Embed(
                    title="❌ Error",
                    description=f"Could not fetch tasks for **{roster_info['name']}**",
                    color=0xff0000
                )
                await ctx.send(embed=embed)
                return
            
            embed = discord.Embed(
                title=f"📋 Remaining Tasks - {roster_info['name']}",
                description=f"Tasks remaining for this week ({remaining_tasks['total_remaining']} total)\nUse `!complete_task <number>` or `!done <number>` to complete",
                color=0x0099ff
            )
            
            # Create numbered list combining personal and household tasks
            all_tasks = []
            task_number = 1
            
            # Personal tasks
            personal_tasks = remaining_tasks["personal"]
            if personal_tasks:
                personal_text = ""
                for task in personal_tasks:
                    doubled_indicator = " ⚠️ *doubled*" if task.get("doubled_from_previous") else ""
                    personal_text += f"`{task_number}.` **{task['name']}** ({task['points']} pts){doubled_indicator}\n"
                    task_number += 1
                
                embed.add_field(
                    name=f"👤 Personal Tasks ({len(personal_tasks)})",
                    value=personal_text[:1024],  # Discord field limit
                    inline=False
                )
            
            # Household tasks
            household_tasks = remaining_tasks["household"]
            if household_tasks:
                household_text = ""
                for task in household_tasks:
                    doubled_indicator = " ⚠️ *doubled*" if task.get("doubled_from_previous") else ""
                    household_text += f"`{task_number}.` **{task['name']}** ({task['points']} pts){doubled_indicator}\n"
                    task_number += 1
                
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
            else:
                embed.add_field(
                    name="💡 Quick Complete",
                    value="Use `!done 1` to complete task #1, or `!complete_task personal Clean bedroom` for full name",
                    inline=False
                )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error listing tasks: {e}")
            await ctx.send("❌ An error occurred while listing tasks.")

    @commands.command(name="completed_tasks", aliases=["completed"])
    async def completed_tasks(self, ctx):
        """List completed cleaning tasks for this week
        Usage: !completed_tasks or !completed
        Must be used in a cleaning roster channel
        """
        try:
            # Check if this is a roster channel
            roster_info = await self._get_roster_from_context(ctx)
            if not roster_info:
                await ctx.send("❌ This command must be used in a cleaning roster channel.")
                return
            
            completed_tasks = await cleaning_manager.get_completed_tasks(roster_info["name"], str(ctx.guild.id))
            
            if completed_tasks is None:
                embed = discord.Embed(
                    title="❌ Error",
                    description=f"Could not fetch completed tasks for **{roster_info['name']}**",
                    color=0xff0000
                )
                await ctx.send(embed=embed)
                return
            
            embed = discord.Embed(
                title=f"✅ Completed Tasks - {roster_info['name']}",
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
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error listing completed tasks: {e}")
            await ctx.send("❌ An error occurred while listing completed tasks.")

    @commands.command(name="points")
    async def points(self, ctx):
        """Show current week's points for all roster members
        Usage: !points
        Must be used in a cleaning roster channel
        """
        try:
            # Check if this is a roster channel
            roster_info = await self._get_roster_from_context(ctx)
            if not roster_info:
                await ctx.send("❌ This command must be used in a cleaning roster channel.")
                return
            
            user_points = await cleaning_manager.get_user_points(roster_info["name"], str(ctx.guild.id))
            
            if user_points is None:
                embed = discord.Embed(
                    title="❌ Error",
                    description=f"Could not fetch points for **{roster_info['name']}**",
                    color=0xff0000
                )
                await ctx.send(embed=embed)
                return
            
            # Get the dynamic weekly goal
            weekly_goal = await cleaning_manager.get_weekly_goal(roster_info["name"], str(ctx.guild.id))
            
            embed = discord.Embed(
                title=f"📊 Weekly Points - {roster_info['name']}",
                description=f"Points earned this week (Goal: {weekly_goal} points per person)",
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
                    if points >= weekly_goal:
                        emoji = "🏆"
                    elif points >= weekly_goal * 0.75:
                        emoji = "🔥"
                    elif points >= 1:
                        emoji = "⭐"
                    else:
                        emoji = "📋"
                    
                    points_text += f"{emoji} **{user_name}**: {points}/{weekly_goal} points\n"
                
                embed.add_field(
                    name="Member Points",
                    value=points_text,
                    inline=False
                )
                
                # Show goal explanation if it's increased
                if weekly_goal > 4:
                    roster_details = await cleaning_manager.get_roster_info(roster_info["name"], str(ctx.guild.id))
                    current_week_data = roster_details["weekly_data"][roster_details["current_week"]]
                    goal_reason = current_week_data.get("goal_increase_reason")
                    
                    if goal_reason:
                        increase = weekly_goal - 4
                        embed.add_field(
                            name=f"⚠️ Increased Goal (+{increase} points)",
                            value=f"Due to {goal_reason['incomplete_tasks']} incomplete tasks from last week\n"
                                  f"Average point increase: {goal_reason['average_increase']:.2f} → +{goal_reason['goal_increase']} to goal",
                            inline=False
                        )
            else:
                embed.add_field(
                    name="No points yet",
                    value="No one has completed any tasks this week.",
                    inline=False
                )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error showing points: {e}")
            await ctx.send("❌ An error occurred while showing points.")

    @commands.command(name="lifetime_points", aliases=["lifetime"])
    async def lifetime_points(self, ctx):
        """Show lifetime points for all roster members
        Usage: !lifetime_points or !lifetime
        Must be used in a cleaning roster channel
        """
        try:
            # Check if this is a roster channel
            roster_info = await self._get_roster_from_context(ctx)
            if not roster_info:
                await ctx.send("❌ This command must be used in a cleaning roster channel.")
                return
            
            lifetime_points = await cleaning_manager.get_lifetime_points(roster_info["name"], str(ctx.guild.id))
            
            if lifetime_points is None:
                embed = discord.Embed(
                    title="❌ Error",
                    description=f"Could not fetch lifetime points for **{roster_info['name']}**",
                    color=0xff0000
                )
                await ctx.send(embed=embed)
                return
            
            embed = discord.Embed(
                title=f"🏆 Lifetime Points - {roster_info['name']}",
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
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error showing lifetime points: {e}")
            await ctx.send("❌ An error occurred while showing lifetime points.")

    @commands.command(name="roster_info", aliases=["roster", "info"])
    async def roster_info(self, ctx):
        """Show information about this cleaning roster
        Usage: !roster_info, !roster, or !info
        Must be used in a cleaning roster channel
        """
        try:
            # Check if this is a roster channel
            roster_info = await self._get_roster_from_context(ctx)
            if not roster_info:
                await ctx.send("❌ This command must be used in a cleaning roster channel.")
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
                value="\n".join([f"• {name}" for name in member_names]) if member_names else "No members yet",
                inline=True
            )
            
            # Task counts (different for personal vs household)
            current_week_data = roster_info["weekly_data"][roster_info["current_week"]]
            personal_count = len(current_week_data["remaining_tasks"]["personal"])  # Personal: current week only
            household_base_count = len(roster_info["base_tasks"]["household"])  # Household: base recurring tasks
            
            embed.add_field(
                name="📋 Tasks",
                value=f"Personal (one-time): {personal_count}\nHousehold (recurring): {household_base_count}",
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
            
            # Add help text
            embed.add_field(
                name="📖 Available Commands",
                value=(
                    "`!add_member @user` - Add member\n"
                    "`!add_task personal <pts> <name>` - One-time task\n"
                    "`!add_task household <pts> <name>` - Recurring task\n"
                    "`!tasks` - Show numbered task list\n"
                    "`!done <number>` - Complete task by number\n"
                    "`!completed` - Show completed tasks\n"
                    "`!points` - Show weekly points\n"
                    "`!lifetime` - Show lifetime points"
                ),
                inline=False
            )
            
            # Get the dynamic weekly goal for footer
            try:
                weekly_goal = await cleaning_manager.get_weekly_goal(roster_info["name"], str(ctx.guild.id))
                goal_text = f"Goal: {weekly_goal} points/week"
                if weekly_goal > 4:
                    goal_text += f" (+{weekly_goal-4} from incomplete tasks)"
            except:
                goal_text = "Goal: 4 points/week"
            
            embed.set_footer(text=f"Household tasks reset weekly • Personal tasks are one-time • {goal_text}")
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error showing roster info: {e}")
            await ctx.send("❌ An error occurred while showing roster info.")

    @commands.command(name="my_rosters")
    async def my_rosters(self, ctx):
        """List all cleaning rosters you're a member of
        Usage: !my_rosters
        """
        try:
            guild_rosters = await cleaning_manager.get_guild_rosters(str(ctx.guild.id))
            user_rosters = []
            
            for roster in guild_rosters:
                if str(ctx.author.id) in roster["members"]:
                    user_rosters.append(roster)
            
            if user_rosters:
                embed = discord.Embed(
                    title="🧹 Your Cleaning Rosters",
                    description=f"You are a member of {len(user_rosters)} roster(s)",
                    color=0x0099ff
                )
                
                for roster in user_rosters:
                    channel_mention = "No channel"
                    if roster["channel_id"]:
                        channel = self.bot.get_channel(int(roster["channel_id"]))
                        if channel:
                            channel_mention = channel.mention
                    
                    embed.add_field(
                        name=roster["name"],
                        value=f"Channel: {channel_mention}\nMembers: {len(roster['members'])}",
                        inline=False
                    )
            else:
                embed = discord.Embed(
                    title="📋 No Rosters",
                    description="You are not a member of any cleaning rosters.\nAsk someone to add you with `!add_member` or create your own with `!create_roster`",
                    color=0xff9900
                )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error listing user rosters: {e}")
            await ctx.send("❌ An error occurred while listing your rosters.")


async def setup(bot):
    await bot.add_cog(CleaningCommands(bot))