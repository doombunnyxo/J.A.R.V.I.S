"""
Central admin command processor that handles all admin logic
"""
import re
from typing import Dict, Optional, Any
from datetime import datetime
import discord
from groq import Groq
from openai import AsyncOpenAI
import aiohttp
import json

from ..config import config
from ..utils.logging import get_logger
from .parser import AdminIntentParser
from .permissions import is_admin
from .actions import AdminActionHandler

logger = get_logger(__name__)


class AdminProcessor:
    """Centralized admin command processing"""
    
    def __init__(self, bot, ai_handler=None):
        self.bot = bot
        self.ai_handler = ai_handler
        self.parser = AdminIntentParser(bot)
        self.actions = AdminActionHandler(bot)
        self.groq_client = Groq(api_key=config.GROQ_API_KEY) if config.has_groq_api() else None
        
        # Track pending admin actions
        self.pending_admin_actions = {}
    
    async def process_admin_command(self, message, query: str) -> str:
        """Main entry point for processing admin commands"""
        try:
            # Check admin permissions
            if not is_admin(message.author.id):
                return "❌ You don't have permission to use admin commands."
            
            # Check if this needs web search (role reorganization)
            if await self._needs_role_search(query):
                return await self._handle_role_reorganization(message, query)
            else:
                # Standard admin command
                return await self._handle_standard_admin(message, query)
                
        except Exception as e:
            logger.error(f"Admin processing failed: {e}")
            return f"❌ Error processing admin command: {str(e)}"
    
    async def _needs_role_search(self, query: str) -> bool:
        """Check if command needs web search for role reorganization"""
        query_lower = query.lower()
        
        # Role reorganization keywords
        role_patterns = [
            'reorganize.*roles', 'rename.*roles', 'fix.*roles', 'update.*roles',
            'change.*roles', 'roles.*based on', 'roles.*match', 'roles.*like',
            'roles.*theme', 'make.*roles', 'set.*roles'
        ]
        
        return any(re.search(pattern, query_lower) for pattern in role_patterns)
    
    async def _handle_role_reorganization(self, message, query: str) -> str:
        """Handle role reorganization commands that need web search"""
        try:
            # Analyze command to get search details
            analysis = await self._analyze_role_command(query)
            
            if not analysis.get('theme'):
                return "❌ Could not identify theme for role reorganization."
            
            # Perform web search
            search_results = await self._search_for_theme(analysis['search_query'])
            
            if not search_results or search_results.startswith("❌"):
                return f"❌ Failed to search for {analysis['theme']} information."
            
            # Generate role list using OpenAI
            role_list = await self._generate_role_list(query, search_results, analysis['theme'])
            
            if not role_list or role_list.startswith("❌"):
                return role_list or "❌ Failed to generate role list"
            
            # Create confirmation message
            return await self._create_role_confirmation(message, query, role_list, analysis)
            
        except Exception as e:
            logger.error(f"Role reorganization failed: {e}")
            return f"❌ Error with role reorganization: {str(e)}"
    
    async def _handle_standard_admin(self, message, query: str) -> str:
        """Handle standard admin commands"""
        try:
            # Use the existing parser
            action_type, parameters = await self.parser.parse_admin_intent(
                query, message.guild, message.author
            )
            
            if not action_type or not parameters:
                return None  # Let the AI handle it as a regular message
            
            # Create confirmation message
            confirmation = self._format_confirmation(action_type, parameters)
            
            # Store pending action
            action_data = {
                'action_type': action_type,
                'parameters': parameters,
                'requester_id': message.author.id,
                'timestamp': datetime.now()
            }
            
            # Send confirmation with reactions
            bot_message = await message.channel.send(confirmation)
            await bot_message.add_reaction('✅')
            await bot_message.add_reaction('❌')
            
            # Store the pending action
            self.pending_admin_actions[bot_message.id] = action_data
            
            return ""  # Empty response since we sent our own message
            
        except Exception as e:
            logger.error(f"Standard admin processing failed: {e}")
            return f"❌ Error processing admin command: {str(e)}"
    
    async def _analyze_role_command(self, query: str) -> dict:
        """Analyze role reorganization command using Groq"""
        try:
            if not self.groq_client:
                # Fallback to regex extraction
                return self._extract_theme_fallback(query)
            
            system_message = """Extract the theme/franchise for role reorganization.
Return JSON with:
{
  "theme": "detected theme name",
  "search_query": "optimized search query for the theme"
}"""
            
            completion = self.groq_client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": f"Extract theme from: {query}"}
                ],
                max_tokens=100,
                temperature=0.1
            )
            
            response = completion.choices[0].message.content.strip()
            return json.loads(response)
            
        except Exception as e:
            logger.error(f"Theme analysis failed: {e}")
            return self._extract_theme_fallback(query)
    
    def _extract_theme_fallback(self, query: str) -> dict:
        """Fallback theme extraction using regex"""
        query_lower = query.lower()
        
        # Common patterns
        patterns = [
            r'based on\s+(.+?)(?:\s+theme|\s+universe|\s+franchise|$)',
            r'like\s+(.+?)(?:\s+theme|\s+universe|\s+franchise|$)',
            r'match\s+(.+?)(?:\s+theme|\s+universe|\s+franchise|$)',
            r'from\s+(.+?)(?:\s+theme|\s+universe|\s+franchise|$)',
            r'theme[:\s]+(.+?)(?:\s+roles|$)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, query_lower)
            if match:
                theme = match.group(1).strip()
                return {
                    "theme": theme.title(),
                    "search_query": f"{theme} hierarchy factions groups roles characters"
                }
        
        # Default extraction - take last few words
        words = query.split()
        theme = ' '.join(words[-3:]) if len(words) > 3 else ' '.join(words)
        return {
            "theme": theme,
            "search_query": f"{theme} hierarchy factions groups roles"
        }
    
    async def _search_for_theme(self, search_query: str) -> str:
        """Perform Google search for theme information"""
        try:
            if not config.has_google_api():
                return "❌ Google search not configured"
            
            url = "https://www.googleapis.com/customsearch/v1"
            params = {
                'key': config.GOOGLE_API_KEY,
                'cx': config.GOOGLE_SEARCH_ENGINE_ID,
                'q': search_query,
                'num': 5
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status != 200:
                        return f"❌ Search failed: {response.status}"
                    
                    data = await response.json()
                    
                    if 'items' not in data:
                        return "❌ No search results found"
                    
                    # Format results
                    results = []
                    for item in data['items']:
                        results.append(f"Title: {item.get('title', 'N/A')}")
                        results.append(f"Snippet: {item.get('snippet', 'N/A')}")
                        results.append("---")
                    
                    return '\n'.join(results)
                    
        except Exception as e:
            logger.error(f"Google search failed: {e}")
            return f"❌ Search error: {str(e)}"
    
    async def _generate_role_list(self, query: str, search_results: str, theme: str) -> str:
        """Generate role list using OpenAI GPT-4o mini"""
        try:
            if not config.has_openai_api():
                return "❌ OpenAI not configured for role generation"
            
            client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)
            
            system_message = """Generate Discord role names based on search results.
Output ONLY role names, one per line, hierarchical order (highest to lowest).
No explanations, no formatting, just role names."""
            
            user_message = f"""Theme: {theme}
Request: {query}

Search Results:
{search_results[:4000]}

Generate role list:"""
            
            completion = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_message}
                ],
                max_tokens=300,
                temperature=0.2
            )
            
            return completion.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Role generation failed: {e}")
            return f"❌ Error generating roles: {str(e)}"
    
    async def _create_role_confirmation(self, message, query: str, role_list: str, analysis: dict) -> str:
        """Create confirmation message for role reorganization"""
        # Parse role list
        roles = [role.strip() for role in role_list.split('\n') if role.strip()]
        
        if not roles:
            return "❌ No roles were generated"
        
        # Create formatted message
        confirmation = f"🎭 **Role Reorganization Request**\n\n"
        confirmation += f"**Theme:** {analysis['theme']}\n"
        confirmation += f"**Current Server:** {message.guild.name}\n\n"
        confirmation += "**Proposed Role Hierarchy:**\n"
        
        for i, role in enumerate(roles, 1):
            confirmation += f"{i}. {role}\n"
        
        confirmation += f"\n⚠️ **Warning:** This will rename ALL {len(message.guild.roles)-1} server roles!\n"
        confirmation += "React with ✅ to confirm or ❌ to cancel."
        
        # Store pending action
        action_data = {
            'action_type': 'reorganize_roles',
            'role_list': roles,
            'theme': analysis['theme'],
            'requester_id': message.author.id,
            'timestamp': datetime.now()
        }
        
        # Send confirmation
        bot_message = await message.channel.send(confirmation)
        await bot_message.add_reaction('✅')
        await bot_message.add_reaction('❌')
        
        # Store the pending action
        self.pending_admin_actions[bot_message.id] = action_data
        
        return ""  # Empty response since we sent our own message
    
    def _format_confirmation(self, action_type: str, parameters: dict) -> str:
        """Format confirmation message for standard admin actions"""
        confirmations = {
            'kick_user': lambda p: f"🦵 Kick user **{p['user']}**" + (f" - Reason: {p['reason']}" if p.get('reason') else ""),
            'ban_user': lambda p: f"🔨 Ban user **{p['user']}**" + (f" - Reason: {p['reason']}" if p.get('reason') else ""),
            'unban_user': lambda p: f"✅ Unban user **{p['user']}**",
            'timeout_user': lambda p: f"⏰ Timeout **{p['user']}** for {p['duration']} minute(s)" + (f" - Reason: {p['reason']}" if p.get('reason') else ""),
            'remove_timeout': lambda p: f"✅ Remove timeout from **{p['user']}**",
            'change_nickname': lambda p: f"✏️ Change **{p['user']}'s** nickname to **{p['nickname']}**",
            'add_role': lambda p: f"➕ Add role **{p['role']}** to **{p['user']}**",
            'remove_role': lambda p: f"➖ Remove role **{p['role']}** from **{p['user']}**",
            'rename_role': lambda p: f"✏️ Rename role **{p['old_name']}** to **{p['new_name']}**",
            'bulk_delete': lambda p: self._format_bulk_delete(p),
            'create_channel': lambda p: f"➕ Create {p['type']} channel **{p['name']}**" + (f" in category {p['category']}" if p.get('category') else ""),
            'delete_channel': lambda p: f"🗑️ Delete channel **{p['channel']}**"
        }
        
        formatter = confirmations.get(action_type)
        if not formatter:
            return f"❓ Unknown action: {action_type}"
        
        confirmation = formatter(parameters)
        return f"{confirmation}\n\nReact with ✅ to confirm or ❌ to cancel."
    
    def _format_bulk_delete(self, params: dict) -> str:
        """Format bulk delete confirmation"""
        base = f"🗑️ Delete {params['count']} messages"
        if params.get('user'):
            base += f" from **{params['user']}**"
        if params.get('channel') and params['channel'] != 'current':
            base += f" in #{params['channel']}"
        return base
    
    async def handle_admin_reaction(self, reaction, user):
        """Handle confirmation reactions for admin actions"""
        message_id = reaction.message.id
        
        if message_id not in self.pending_admin_actions:
            return
        
        action_data = self.pending_admin_actions[message_id]
        
        # Check if reactor is the original requester
        if user.id != action_data['requester_id']:
            return
        
        if str(reaction.emoji) == '✅':
            # Execute the action
            result = await self._execute_admin_action(
                reaction.message, 
                action_data
            )
            await reaction.message.edit(content=result)
        elif str(reaction.emoji) == '❌':
            await reaction.message.edit(content="❌ Admin action cancelled.")
        
        # Clean up
        del self.pending_admin_actions[message_id]
        await reaction.message.clear_reactions()
    
    async def _execute_admin_action(self, message, action_data: dict) -> str:
        """Execute the confirmed admin action"""
        try:
            action_type = action_data['action_type']
            
            if action_type == 'reorganize_roles':
                # Special handling for role reorganization
                return await self._execute_role_reorganization(
                    message,
                    action_data['role_list'],
                    action_data['theme']
                )
            else:
                # Standard admin actions
                result_msg = await self.actions.execute_admin_action(
                    message,
                    action_type,
                    action_data['parameters']
                )
                
                return result_msg
                    
        except Exception as e:
            logger.error(f"Admin action execution failed: {e}")
            return f"❌ Error executing action: {str(e)}"
    
    async def _execute_role_reorganization(self, message, role_list: list, theme: str) -> str:
        """Execute role reorganization"""
        try:
            guild = message.guild
            renamed_count = 0
            errors = []
            
            # Get manageable roles (exclude @everyone and bot's highest role)
            manageable_roles = [r for r in guild.roles[1:] if r < guild.me.top_role]
            
            # Rename roles
            for i, role in enumerate(manageable_roles):
                if i < len(role_list):
                    try:
                        old_name = role.name
                        await role.edit(name=role_list[i])
                        renamed_count += 1
                        logger.info(f"Renamed role '{old_name}' to '{role_list[i]}'")
                    except discord.Forbidden:
                        errors.append(f"No permission to rename '{role.name}'")
                    except Exception as e:
                        errors.append(f"Failed to rename '{role.name}': {str(e)}")
            
            # Build result message
            result = f"✅ **Role Reorganization Complete!**\n\n"
            result += f"**Theme:** {theme}\n"
            result += f"**Roles Renamed:** {renamed_count}/{len(manageable_roles)}\n"
            
            if errors:
                result += f"\n**Errors:**\n"
                for error in errors[:5]:  # Limit error display
                    result += f"• {error}\n"
                if len(errors) > 5:
                    result += f"• ... and {len(errors)-5} more errors\n"
            
            return result
            
        except Exception as e:
            logger.error(f"Role reorganization failed: {e}")
            return f"❌ Role reorganization failed: {str(e)}"