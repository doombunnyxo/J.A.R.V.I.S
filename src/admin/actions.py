import discord
import asyncio
import re
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, Any
from .permissions import is_admin

class AdminActionHandler:
    """Handles Discord server administrative actions"""
    
    def __init__(self, bot):
        self.bot = bot
    
    async def execute_admin_action(self, message, action_type: str, parameters: Dict[str, Any]) -> str:
        """Execute administrative actions based on AI interpretation"""
        print(f"DEBUG: execute_admin_action called with action_type: {action_type}")
        print(f"DEBUG: execute_admin_action parameters: {parameters}")
        
        if not is_admin(message.author.id):
            return "❌ **Access Denied**: You don't have permission to perform admin actions."
        
        try:
            guild = message.guild
            if not guild:
                return "❌ Admin actions can only be performed in servers, not DMs."
            
            admin_user = message.author
            reason_suffix = f" (Requested by {admin_user.name}#{admin_user.discriminator})"
            
            # Route to specific action handler
            if action_type == "kick_user":
                return await self._handle_kick_user(parameters, admin_user, reason_suffix)
            elif action_type == "ban_user":
                return await self._handle_ban_user(parameters, admin_user, reason_suffix)
            elif action_type == "unban_user":
                return await self._handle_unban_user(parameters, guild)
            elif action_type == "timeout_user":
                return await self._handle_timeout_user(parameters, admin_user, reason_suffix)
            elif action_type == "remove_timeout":
                return await self._handle_remove_timeout(parameters, admin_user)
            elif action_type == "add_role":
                return await self._handle_add_role(parameters, admin_user)
            elif action_type == "remove_role":
                return await self._handle_remove_role(parameters, admin_user)
            elif action_type == "rename_role":
                return await self._handle_rename_role(parameters, admin_user)
            elif action_type == "reorganize_roles":
                return await self._handle_reorganize_roles(parameters, admin_user)
            elif action_type == "bulk_delete":
                return await self._handle_bulk_delete(parameters, message, admin_user)
            elif action_type == "create_channel":
                return await self._handle_create_channel(parameters, guild, admin_user)
            elif action_type == "delete_channel":
                return await self._handle_delete_channel(parameters, admin_user)
            elif action_type == "change_nickname":
                return await self._handle_change_nickname(parameters, admin_user)
            else:
                return f"❌ **Unknown Action**: '{action_type}' is not a recognized admin action."
        
        except discord.Forbidden:
            return "❌ **Permission Error**: Bot lacks necessary permissions for this action."
        except discord.NotFound:
            return "❌ **Not Found**: The specified user, role, or channel was not found."
        except Exception as e:
            return f"❌ **Error**: {str(e)}"
    
    async def _handle_kick_user(self, parameters: dict, admin_user, reason_suffix: str) -> str:
        """Handle user kick action"""
        user = parameters.get("user")
        base_reason = parameters.get("reason", "Admin action via AI")
        reason = base_reason + reason_suffix
        
        if user:
            await user.kick(reason=reason)
            return f"✅ **User Kicked**: {user.mention} has been kicked.\n**Reason**: {base_reason}\n**Requested by**: {admin_user.mention}"
        return "❌ **Error**: No user specified for kick action."
    
    async def _handle_ban_user(self, parameters: dict, admin_user, reason_suffix: str) -> str:
        """Handle user ban action"""
        user = parameters.get("user")
        base_reason = parameters.get("reason", "Admin action via AI")
        reason = base_reason + reason_suffix
        delete_days = parameters.get("delete_days", 0)
        
        if user:
            await user.ban(reason=reason, delete_message_days=delete_days)
            return f"✅ **User Banned**: {user.mention} has been banned.\n**Reason**: {base_reason}\n**Messages deleted**: {delete_days} days\n**Requested by**: {admin_user.mention}"
        return "❌ **Error**: No user specified for ban action."
    
    async def _handle_unban_user(self, parameters: dict, guild) -> str:
        """Handle user unban action"""
        user_id = parameters.get("user_id")
        if user_id:
            user = await self.bot.fetch_user(user_id)
            await guild.unban(user)
            return f"✅ **User Unbanned**: {user.mention} has been unbanned."
        return "❌ **Error**: No user ID specified for unban action."
    
    async def _handle_timeout_user(self, parameters: dict, admin_user, reason_suffix: str) -> str:
        """Handle user timeout action"""
        user = parameters.get("user")
        duration = parameters.get("duration", 60)
        base_reason = parameters.get("reason", "Admin action via AI")
        reason = base_reason + reason_suffix
        
        if user:
            timeout_until = datetime.now() + timedelta(minutes=duration)
            await user.timeout(timeout_until, reason=reason)
            return f"✅ **User Timed Out**: {user.mention} has been timed out for {duration} minutes.\n**Reason**: {base_reason}\n**Requested by**: {admin_user.mention}"
        return "❌ **Error**: No user specified for timeout action."
    
    async def _handle_remove_timeout(self, parameters: dict, admin_user) -> str:
        """Handle remove timeout action"""
        user = parameters.get("user")
        if user:
            await user.timeout(None)
            return f"✅ **Timeout Removed**: {user.mention} timeout has been removed.\n**Requested by**: {admin_user.mention}"
        return "❌ **Error**: No user specified for remove timeout action."
    
    async def _handle_add_role(self, parameters: dict, admin_user) -> str:
        """Handle add role action"""
        user = parameters.get("user")
        role = parameters.get("role")
        
        print(f"DEBUG: Add role - user: {user}, role: {role}")
        
        if not user:
            return "❌ **Error**: Could not find the user to add role to. Please mention the user or use their exact username."
        
        if not role:
            return "❌ **Error**: Could not find the role to add. Please use quotes around the role name if it contains spaces (e.g., \"Trusted Member\")."
        
        try:
            await user.add_roles(role, reason=f"Role added by admin {admin_user.name}")
            return f"✅ **Role Added**: {role.name} has been added to {user.mention}.\n**Requested by**: {admin_user.mention}"
        except discord.Forbidden:
            return f"❌ **Permission Error**: I don't have permission to add the role '{role.name}' or it's higher than my highest role.\n**Requested by**: {admin_user.mention}"
        except Exception as e:
            return f"❌ **Error**: Failed to add role: {str(e)}\n**Requested by**: {admin_user.mention}"
    
    async def _handle_remove_role(self, parameters: dict, admin_user) -> str:
        """Handle remove role action"""
        user = parameters.get("user")
        role = parameters.get("role")
        
        print(f"DEBUG: Remove role - user: {user}, role: {role}")
        
        if not user:
            return "❌ **Error**: Could not find the user to remove role from. Please mention the user or use their exact username."
        
        if not role:
            return "❌ **Error**: Could not find the role to remove. Please use quotes around the role name if it contains spaces (e.g., \"Trusted Member\")."
        
        try:
            await user.remove_roles(role, reason=f"Role removed by admin {admin_user.name}")
            return f"✅ **Role Removed**: {role.name} has been removed from {user.mention}.\n**Requested by**: {admin_user.mention}"
        except discord.Forbidden:
            return f"❌ **Permission Error**: I don't have permission to remove the role '{role.name}' or it's higher than my highest role.\n**Requested by**: {admin_user.mention}"
        except Exception as e:
            return f"❌ **Error**: Failed to remove role: {str(e)}\n**Requested by**: {admin_user.mention}"
    
    async def _handle_rename_role(self, parameters: dict, admin_user) -> str:
        """Handle role renaming action"""
        role = parameters.get("role")
        new_name = parameters.get("new_name")
        
        print(f"DEBUG: Rename role - role: {role}, new_name: '{new_name}'")
        
        if not role:
            return "❌ **Error**: Could not find the role to rename. Please use quotes around the role name if it contains spaces (e.g., \"Old Role Name\")."
        
        if not new_name:
            return "❌ **Error**: New name not specified for role rename. Use format: 'rename role \"Old Name\" to \"New Name\"'."
        
        # Check if the new name is valid (Discord role name limits)
        if len(new_name) > 100:
            return "❌ **Error**: Role name too long (max 100 characters)."
        
        if not new_name.strip():
            return "❌ **Error**: Role name cannot be empty."
        
        old_name = role.name
        
        try:
            await role.edit(name=new_name, reason=f"Role renamed by {admin_user.name}")
            return f"✅ **Role Renamed**: '{old_name}' has been renamed to '{new_name}'.\n**Requested by**: {admin_user.mention}"
        except discord.Forbidden:
            return f"❌ **Permission Error**: I don't have permission to rename the role '{old_name}'. Make sure the bot's role is higher than this role.\n**Requested by**: {admin_user.mention}"
        except discord.HTTPException as e:
            if "Invalid Form Body" in str(e):
                return f"❌ **Invalid Role Name**: The name '{new_name}' is not valid for Discord roles. Try a different name.\n**Requested by**: {admin_user.mention}"
            return f"❌ **Error**: Failed to rename role '{old_name}': {str(e)}\n**Requested by**: {admin_user.mention}"
    
    async def _handle_bulk_delete(self, parameters: dict, message, admin_user) -> str:
        """Handle bulk message deletion"""
        channel = parameters.get("channel") or message.channel
        limit = parameters.get("limit", 100)
        user_filter = parameters.get("user_filter")
        
        if channel is None:
            return f"❌ **Error**: Could not determine which channel to delete messages from.\n**Requested by**: {admin_user.mention}"
        
        deleted_count = 0
        checked_count = 0
        
        try:
            search_limit = min(limit * 10, 1000) if user_filter else limit
            
            async for msg in channel.history(limit=search_limit):
                checked_count += 1
                
                # If we've deleted enough messages, stop
                if deleted_count >= limit:
                    break
                
                # Debug: Show message details
                print(f"DEBUG: Checking message {msg.id} from {msg.author.name} (ID: {msg.author.id})")
                if user_filter:
                    print(f"DEBUG: User filter set for {user_filter.name} (ID: {user_filter.id})")
                
                # If we have a user filter and this message isn't from that user, skip it
                if user_filter and msg.author.id != user_filter.id:
                    print(f"DEBUG: Skipping message from {msg.author.name} - not target user {user_filter.name}")
                    continue
                
                print(f"DEBUG: Attempting to delete message from {msg.author.name}")
                
                # Delete the message
                try:
                    await msg.delete()
                    deleted_count += 1
                    print(f"DEBUG: Successfully deleted message {msg.id}")
                    await asyncio.sleep(1.0)  # Rate limit protection
                except Exception as e:
                    print(f"DEBUG: Failed to delete message {msg.id}: {e}")
                    continue
            
            if checked_count == 0:
                return f"⚠️ **No Messages Found**: Bot can only see messages sent after it came online.\n**Requested by**: {admin_user.mention}"
            elif deleted_count == 0:
                if user_filter:
                    return f"⚠️ **No Messages Deleted**: Found {checked_count} messages but none from {user_filter.mention}.\n**Requested by**: {admin_user.mention}"
                else:
                    return f"⚠️ **No Messages Deleted**: Found {checked_count} messages but couldn't delete any.\n**Requested by**: {admin_user.mention}"
            else:
                if user_filter:
                    return f"✅ **Bulk Delete Complete**: Deleted {deleted_count} messages from {user_filter.mention} in {channel.mention}.\n**Requested by**: {admin_user.mention}"
                else:
                    return f"✅ **Bulk Delete Complete**: Deleted {deleted_count} messages in {channel.mention}.\n**Requested by**: {admin_user.mention}"
        
        except Exception as e:
            print(f"DEBUG: Error accessing channel history: {e}")
            return f"❌ **Error**: Could not access channel history in {channel.mention}. Error: {str(e)}\n**Requested by**: {admin_user.mention}"
    
    async def _handle_create_channel(self, parameters: dict, guild, admin_user) -> str:
        """Handle channel creation"""
        name = parameters.get("name")
        channel_type = parameters.get("type", "text")
        
        if name:
            if channel_type == "voice":
                new_channel = await guild.create_voice_channel(name)
            else:
                new_channel = await guild.create_text_channel(name)
            return f"✅ **Channel Created**: {new_channel.mention} has been created.\n**Requested by**: {admin_user.mention}"
        return "❌ **Error**: No channel name specified."
    
    async def _handle_delete_channel(self, parameters: dict, admin_user) -> str:
        """Handle channel deletion"""
        channel = parameters.get("channel")
        if channel:
            channel_name = channel.name
            await channel.delete()
            return f"✅ **Channel Deleted**: #{channel_name} has been deleted.\n**Requested by**: {admin_user.mention}"
        return "❌ **Error**: No channel specified for deletion."
    
    async def _handle_change_nickname(self, parameters: dict, admin_user) -> str:
        """Handle nickname change"""
        user = parameters.get("user")
        nickname = parameters.get("nickname")
        
        if user:
            # Check if user is a Member object (required for editing nicknames)
            if not isinstance(user, discord.Member):
                return f"❌ **Error**: Cannot change nickname - user must be a server member, not a User object.\n**Requested by**: {admin_user.mention}"
            
            try:
                old_nick = user.display_name
                await user.edit(nick=nickname, reason=f"Nickname changed by {admin_user.name}")
                return f"✅ **Nickname Changed**: {user.mention} nickname changed from '{old_nick}' to '{nickname or user.name}'.\n**Requested by**: {admin_user.mention}"
            except discord.Forbidden:
                return f"❌ **Permission Error**: I don't have permission to change {user.mention}'s nickname. Make sure the bot's role is higher than the user's highest role.\n**Requested by**: {admin_user.mention}"
            except discord.HTTPException as e:
                return f"❌ **Error**: Failed to change nickname: {str(e)}\n**Requested by**: {admin_user.mention}"
        return "❌ **Error**: No user specified for nickname change."
    
    async def _handle_reorganize_roles(self, parameters: dict, admin_user) -> str:
        """Handle intelligent role reorganization with custom context"""
        guild = parameters.get("guild")
        context_description = parameters.get("context", "general community server")
        research_context = parameters.get("research_context")  # New: research context from multi-step actions
        
        print(f"DEBUG: Role reorganization - guild: {guild}, context: '{context_description}'")
        print(f"DEBUG: Research context available: {bool(research_context)}")
        
        if not guild:
            return "❌ **Error**: Guild not specified for role reorganization."
        
        # Get all roles (exclude @everyone and bot roles)
        roles_to_analyze = []
        for role in guild.roles:
            if role.name != "@everyone" and not role.managed:
                roles_to_analyze.append(role)
        
        if not roles_to_analyze:
            return "❌ **Error**: No roles found that can be reorganized."
        
        print(f"DEBUG: Found {len(roles_to_analyze)} roles to analyze")
        
        # Import here to avoid circular imports
        from ..config import config
        import aiohttp
        
        if not config.has_anthropic_api():
            return "❌ **Error**: Claude API not available for role analysis."
        
        try:
            
            # Prepare role analysis prompt
            role_list = [f"- {role.name}" for role in roles_to_analyze]
            role_text = "\n".join(role_list)
            
            # Build enhanced prompt with research context if available
            if research_context:
                prompt = f"""You are renaming Discord server roles based on comprehensive research and context.

SERVER CONTEXT/DESCRIPTION:
{context_description}

RESEARCH CONTEXT:
{research_context}

CURRENT ROLES TO ANALYZE:
{role_text}

INSTRUCTIONS:
1. Use the research context above to understand the specific terminology, hierarchy, and organizational structure appropriate for this theme/context
2. Create role names that authentically fit the researched theme while maintaining Discord server functionality
3. Maintain existing hierarchy levels (admin > moderator > member, etc.) but use theme-appropriate terminology
4. Draw specific role names, ranks, and terminology from the research context provided
5. Ensure names are recognizable to fans/members of this community while being clear and professional
6. Only suggest renames for roles that would benefit from thematic change
7. Use the most authentic and recognizable terminology from the research context

OUTPUT FORMAT - RESPOND WITH ONLY THIS:
For each role that needs renaming, write exactly:
OLD_NAME → NEW_NAME

For roles that are already appropriate for the context, don't include them.
Do not include any other text, explanations, or formatting beyond the rename pairs."""
            else:
                # Original prompt for cases without research
                prompt = f"""You are renaming Discord server roles based on the following context and requirements.

SERVER CONTEXT/DESCRIPTION:
{context_description}

CURRENT ROLES TO ANALYZE:
{role_text}

INSTRUCTIONS:
1. Analyze the context description above to understand what type of server this is and what role naming style would be appropriate
2. Create role names that fit the context/theme described
3. Maintain any existing hierarchy (admin > moderator > member, etc.)
4. Use consistent naming patterns that make sense for this specific context
5. Make names clear, professional, and appropriate for the described server type
6. Only suggest renames for roles that would benefit from the change
7. If the context describes specific terminology, roles, or structure, incorporate that into the new names

EXAMPLES based on context:
- For a gaming community: Player, VIP Member, Moderator, Guild Leader, Veteran, Streamer
- For a business/professional server: Team Member, Manager, Director, Client, Partner
- For an educational server: Student, Teaching Assistant, Instructor, Alumni, Researcher
- For a creative community: Creator, Collaborator, Critic, Supporter, Featured Artist
- For specific topics (like music, art, coding): use terminology relevant to that field

OUTPUT FORMAT - RESPOND WITH ONLY THIS:
For each role that needs renaming, write exactly:
OLD_NAME → NEW_NAME

For roles that are already appropriate for the context, don't include them.
Do not include any other text, explanations, or formatting beyond the rename pairs."""

            print(f"DEBUG: Sending flexible prompt to Claude with context: '{context_description}'")
            
            # Make API call to Claude Haiku
            headers = {
                "x-api-key": config.ANTHROPIC_API_KEY,
                "Content-Type": "application/json",
                "anthropic-version": "2023-06-01"
            }
            
            system_content = "You are a Discord server management expert who creates appropriate role names based on specific server contexts and descriptions. Always follow the exact output format requested."
            
            payload = {
                "model": "claude-3-5-haiku-20241022",
                "max_tokens": 800,
                "temperature": 0.3,
                "messages": [
                    {"role": "user", "content": f"{system_content}\n\n{prompt}"}
                ]
            }
            
            timeout = aiohttp.ClientTimeout(total=15)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post("https://api.anthropic.com/v1/messages", 
                                       headers=headers, json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        suggestions = result["content"][0]["text"].strip()
                    else:
                        error_text = await response.text()
                        raise Exception(f"Claude API error {response.status}: {error_text}")
            print(f"DEBUG: AI suggestions received: {suggestions}")
            
            if not suggestions:
                return "❌ **Error**: No suggestions received from AI analysis."
            
            # Parse the suggestions and perform actual renames
            renames_performed = []
            renames_failed = []
            
            # Parse suggestions line by line
            for line in suggestions.split('\n'):
                line = line.strip()
                if '→' in line:
                    try:
                        old_name, new_name = line.split('→', 1)
                        old_name = old_name.strip().strip('"').strip("'")
                        new_name = new_name.strip().strip('"').strip("'")
                        
                        print(f"DEBUG: Trying to rename '{old_name}' to '{new_name}'")
                        
                        # Find the role by name
                        role_to_rename = None
                        for role in roles_to_analyze:
                            if role.name.lower() == old_name.lower():
                                role_to_rename = role
                                break
                        
                        if role_to_rename:
                            try:
                                await role_to_rename.edit(name=new_name, reason=f"Custom role reorganization by {admin_user.name}")
                                renames_performed.append(f"'{old_name}' → '{new_name}'")
                                print(f"DEBUG: Successfully renamed '{old_name}' to '{new_name}'")
                            except discord.Forbidden:
                                renames_failed.append(f"'{old_name}' (permission denied)")
                                print(f"DEBUG: Permission denied renaming '{old_name}'")
                            except Exception as e:
                                renames_failed.append(f"'{old_name}' ({str(e)})")
                                print(f"DEBUG: Error renaming '{old_name}': {e}")
                        else:
                            renames_failed.append(f"'{old_name}' (role not found)")
                            print(f"DEBUG: Role '{old_name}' not found")
                    
                    except ValueError as e:
                        print(f"DEBUG: Failed to parse line: {line} - {e}")
                        continue
            
            # Build response - show the context that was used
            context_preview = context_description[:100] + "..." if len(context_description) > 100 else context_description
            response = f"🤖 **Role Reorganization Complete**\n**Context Used**: {context_preview}\n\n"
            
            if renames_performed:
                response += f"✅ **Successfully Renamed ({len(renames_performed)}):**\n"
                for rename in renames_performed:
                    response += f"• {rename}\n"
                response += "\n"
            
            if renames_failed:
                response += f"❌ **Failed to Rename ({len(renames_failed)}):**\n"
                for failure in renames_failed:
                    response += f"• {failure}\n"
                response += "\n"
            
            if not renames_performed and not renames_failed:
                response += "ℹ️ **No changes needed** - All role names are already appropriate for this context.\n\n"
            
            response += f"**Requested by**: {admin_user.mention}"
            
            return response
            
        except Exception as e:
            print(f"DEBUG: Exception in role reorganization: {e}")
            return f"❌ **Error**: Failed to reorganize roles: {str(e)}\n**Requested by**: {admin_user.mention}"