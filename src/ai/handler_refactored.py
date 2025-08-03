"""
Refactored AI Handler - Clean and modular implementation
Handles hybrid Groq + Claude AI routing with improved structure
"""

import re
from datetime import datetime, timedelta
from typing import Dict, Optional
from collections import defaultdict, deque

from groq import Groq
from ..config import config
from ..data.persistence import data_manager
from ..admin.permissions import is_admin
from ..admin.actions import AdminActionHandler
from ..admin.parser import AdminIntentParser
from ..search.claude import claude_search_analysis, claude_optimize_search_query
from ..search.google import perform_google_search
from ..utils.message_utils import smart_split_message
from .routing import should_use_claude_for_search, extract_forced_provider, extract_claude_model
from .context_manager import ContextManager
from ..crafting.handler import CraftingHandler


class RateLimiter:
    """Simple rate limiter for AI requests"""
    
    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.user_requests: Dict[int, deque] = defaultdict(deque)
    
    def is_allowed(self, user_id: int) -> bool:
        """Check if user can make a request"""
        now = datetime.now()
        user_queue = self.user_requests[user_id]
        
        # Remove old requests
        while user_queue and user_queue[0] < now - timedelta(seconds=self.window_seconds):
            user_queue.popleft()
        
        # Check limit
        if len(user_queue) < self.max_requests:
            user_queue.append(now)
            return True
        
        return False
    
    def get_reset_time(self, user_id: int) -> Optional[datetime]:
        """Get when rate limit resets"""
        user_queue = self.user_requests[user_id]
        if user_queue:
            return user_queue[0] + timedelta(seconds=self.window_seconds)
        return None


class AIHandler:
    """
    Refactored AI Handler with clean separation of concerns
    
    Responsibilities:
    - Route queries to appropriate AI (Groq vs Claude)
    - Manage conversation context across AIs
    - Handle admin actions with confirmations
    - Rate limiting and error handling
    """
    
    def __init__(self, bot):
        self.bot = bot
        self.groq_client = self._initialize_groq()
        
        # Rate limiting
        self.rate_limiter = RateLimiter(
            config.AI_RATE_LIMIT_REQUESTS,
            config.AI_RATE_LIMIT_WINDOW
        )
        
        # Admin handling
        self.admin_handler = AdminActionHandler(bot)
        self.intent_parser = AdminIntentParser(bot)
        self.pending_admin_actions = {}
        
        # Context management
        self.context_manager = ContextManager(self.groq_client)
        
        # Crafting system
        self.crafting_handler = CraftingHandler(bot)
        
        # Provider tracking
        self.conversation_providers = {}  # Track which AI was used per conversation
        
        # Message deduplication
        self.processed_messages = set()
        self.max_processed_messages = 100
        
        print(f"DEBUG: AIHandler initialized successfully")
    
    def _initialize_groq(self) -> Optional[Groq]:
        """Initialize Groq client"""
        try:
            if config.has_groq_api():
                client = Groq(api_key=config.GROQ_API_KEY)
                print("DEBUG: Groq client initialized successfully")
                return client
            else:
                print("WARNING: Groq API key not configured")
                return None
        except Exception as e:
            print(f"ERROR: Groq initialization failed: {e}")
            return None
    
    def _cleanup_processed_messages(self):
        """Clean up old processed message IDs"""
        if len(self.processed_messages) > self.max_processed_messages:
            old_messages = list(self.processed_messages)[:self.max_processed_messages // 2]
            for msg_id in old_messages:
                self.processed_messages.discard(msg_id)
    
    def _cleanup_stale_admin_actions(self):
        """Clean up expired admin actions"""
        current_time = datetime.now()
        cleanup_threshold = 5 * 60  # 5 minutes
        
        stale_users = [
            user_id for user_id, action_data in self.pending_admin_actions.items()
            if "timestamp" in action_data and 
            (current_time - action_data["timestamp"]).total_seconds() > cleanup_threshold
        ]
        
        for user_id in stale_users:
            print(f"DEBUG: Cleaning up stale admin action for user {user_id}")
            self.pending_admin_actions.pop(user_id, None)
    
    async def handle_ai_command(self, message, ai_query: str, force_provider: str = None):
        """
        Main entry point for AI command processing
        
        Args:
            message: Discord message object
            ai_query: User's query string  
            force_provider: Optional forced provider ("groq" or "claude")
        """
        try:
            # Prevent duplicate processing
            if message.id in self.processed_messages:
                print(f"DEBUG: Message {message.id} already processed")
                return
            
            self.processed_messages.add(message.id)
            self._cleanup_processed_messages()
            
            # Check rate limit
            if not self.rate_limiter.is_allowed(message.author.id):
                await self._handle_rate_limit(message)
                return
            
            # Determine routing and get cleaned query
            provider, cleaned_query = await self._determine_provider_and_query(message, ai_query, force_provider)
            
            # Route to appropriate handler
            if provider == "claude":
                response = await self._handle_with_claude(message, cleaned_query)
            elif provider == "perplexity":
                response = await self._handle_with_perplexity(message, cleaned_query)
            elif provider == "crafting":
                response = await self._handle_with_crafting(message, cleaned_query)
            else:  # groq
                response = await self._handle_with_groq(message, cleaned_query)
            
            # Store conversation context
            if response and not response.startswith("Error"):
                self.context_manager.add_to_conversation(
                    message.author.id, message.channel.id, ai_query, response
                )
            
            # Send response if not already sent (admin actions send their own)
            if response:
                await self._send_response(message, response)
        
        except Exception as e:
            await message.channel.send(f'AI request failed: {str(e)}')
    
    async def _determine_provider_and_query(self, message, query: str, force_provider: str) -> tuple[str, str]:
        """Determine which provider to use and return cleaned query"""
        # Check for forced provider
        if force_provider:
            if force_provider == "claude":
                provider = "claude"
            elif force_provider == "perplexity":
                provider = "perplexity"
            elif force_provider == "crafting":
                provider = "crafting"
            else:
                provider = "groq"
            print(f"DEBUG: Forced to use {provider}")
            return provider, query
        
        # Check for provider syntax in query
        forced_provider, cleaned_query = extract_forced_provider(query)
        if forced_provider:
            print(f"DEBUG: Extracted forced provider: {forced_provider}")
            return forced_provider, cleaned_query
        
        # Use original logic for automatic routing
        provider = await self._determine_provider(message, query, None)
        return provider, query
    
    async def _determine_provider(self, message, query: str, force_provider: str) -> str:
        """Determine which AI provider to use"""
        # Check for forced provider
        if force_provider:
            if force_provider == "claude":
                provider = "claude"
            elif force_provider == "perplexity":
                provider = "perplexity"
            elif force_provider == "crafting":
                provider = "crafting"
            else:
                provider = "groq"
            print(f"DEBUG: Forced to use {provider}")
            return provider
        
        # Check for provider syntax in query
        forced_provider, cleaned_query = extract_forced_provider(query)
        if forced_provider:
            print(f"DEBUG: Extracted forced provider: {forced_provider}")
            return forced_provider
        
        # Check if this is a follow-up conversation
        conversation_key = self.context_manager.get_conversation_key(
            message.author.id, message.channel.id
        )
        
        is_followup = self.context_manager.is_context_fresh(
            message.author.id, message.channel.id
        )
        
        # Route based on query content
        use_claude = should_use_claude_for_search(query)
        
        if is_followup:
            previous_provider = self.conversation_providers.get(conversation_key)
            if use_claude:
                if previous_provider != "claude":
                    print(f"DEBUG: Follow-up switching to Claude (was {previous_provider})")
                else:
                    print(f"DEBUG: Follow-up continuing with Claude")
            else:
                if previous_provider != "groq":
                    print(f"DEBUG: Follow-up switching to Groq (was {previous_provider})")
                else:
                    print(f"DEBUG: Follow-up continuing with Groq")
        else:
            if use_claude:
                print(f"DEBUG: New conversation - routing to Claude for web search")
            else:
                print(f"DEBUG: New conversation - routing to Groq for chat/admin")
        
        # Track provider choice
        provider = "claude" if use_claude else "groq"
        self.conversation_providers[conversation_key] = provider
        
        return provider
    
    async def _handle_with_claude(self, message, query: str) -> str:
        """Handle query with Claude (web search)"""
        try:
            if not config.has_anthropic_api():
                return "Claude API not configured - web search unavailable"
            
            # Get user context
            context = await self.context_manager.build_full_context(
                query, message.author.id, message.channel.id, 
                message.author.display_name, message
            )
            
            # Extract model if admin specified one
            model, cleaned_query = extract_claude_model(query, message.author.id)
            
            # Use the generalized search pipeline
            from ..search.search_pipeline import SearchPipeline
            from ..search.claude_adapter import ClaudeSearchProvider
            
            provider = ClaudeSearchProvider(model)
            pipeline = SearchPipeline(provider)
            
            print(f"DEBUG: Using Claude search pipeline with model: {model}")
            print(f"DEBUG: Context length: {len(context)} chars")
            
            response = await pipeline.search_and_respond(cleaned_query, context)
            
            return self._suppress_link_previews(response)
        
        except Exception as e:
            return f"Error with Claude search: {str(e)}"
    
    async def _handle_with_perplexity(self, message, query: str) -> str:
        """Handle query with Perplexity (web search via Google)"""
        try:
            if not config.has_perplexity_api():
                return "Perplexity API not configured - web search unavailable"
            
            # Get user context
            context = await self.context_manager.build_full_context(
                query, message.author.id, message.channel.id, 
                message.author.display_name, message
            )
            
            # Use the generalized search pipeline
            from ..search.search_pipeline import SearchPipeline
            from ..search.perplexity_adapter import PerplexitySearchProvider
            
            provider = PerplexitySearchProvider()
            pipeline = SearchPipeline(provider)
            
            print(f"DEBUG: Using Perplexity search pipeline")
            print(f"DEBUG: Context length: {len(context)} chars")
            
            response = await pipeline.search_and_respond(query, context)
            
            return self._suppress_link_previews(response)
        
        except Exception as e:
            return f"Error with Perplexity search: {str(e)}"
    
    async def _handle_with_groq(self, message, query: str) -> str:
        """Handle query with Groq (chat/admin)"""
        try:
            if not self.groq_client:
                return "Groq API not configured"
            
            # Get user context
            context = await self._build_groq_context(message, query)
            
            # Build system message
            system_message = self._build_groq_system_message(context, message.author.id)
            
            # Call Groq API
            messages = [
                {"role": "system", "content": system_message},
                {"role": "user", "content": query}
            ]
            
            async with message.channel.typing():
                completion = self.groq_client.chat.completions.create(
                    messages=messages,
                    model=config.AI_MODEL,
                    max_tokens=config.AI_MAX_TOKENS,
                    temperature=config.AI_TEMPERATURE
                )
                
                response = completion.choices[0].message.content or "No response generated."
                
                # Check for admin actions
                admin_handled = await self._handle_admin_actions(message, query, response)
                if admin_handled:
                    return ""  # Admin handler sent its own message
                
                # Prepend model name to response
                model_display = "Groq Llama 3.1" if "llama-3.1" in config.AI_MODEL else "Groq"
                return f"**{model_display}:** {response}"
        
        except Exception as e:
            return f"Error processing with Groq: {str(e)}"
    
    async def _handle_with_crafting(self, message, query: str) -> str:
        """Handle query with crafting system"""
        print(f"DEBUG: _handle_with_crafting called with query: '{query}'")
        try:
            # Handle special list commands
            query_lower = query.lower().strip()
            if query_lower in ['list', 'categories', 'help']:
                return await self._handle_crafting_list()
            elif query_lower in ['weapons', 'list weapons']:
                return await self._handle_crafting_category_list('weapons')
            elif query_lower in ['vehicles', 'list vehicles']:
                return await self._handle_crafting_category_list('vehicles')
            elif query_lower in ['tools', 'list tools']:
                return await self._handle_crafting_category_list('tools')
            
            # Use the existing crafting handler to process the query
            result = await self.crafting_handler._interpret_recipe_request(query)
            
            if isinstance(result, tuple) and len(result) == 2:
                item_name, quantity = result
                
                # Import crafting functions
                from dune_crafting import calculate_materials, get_recipe_info, format_materials_list, format_materials_tree, list_craftable_items
                
                try:
                    # Check if this is a vehicle assembly request
                    if item_name.startswith('VEHICLE_ASSEMBLY|'):
                        return await self._handle_vehicle_assembly_request(item_name, quantity, query)
                    
                    # Get the recipe information for individual items
                    recipe_info = get_recipe_info(item_name)
                    if not recipe_info:
                        return f"❌ **Recipe not found for:** {item_name}\n\nThe LLM should have matched this to a valid recipe. Use `@bot craft: list` to see available categories.\n\n**Debug:** Interpreted query '{query}' as item '{item_name}'"
                    
                    # Calculate total materials needed
                    total_materials = calculate_materials(item_name, quantity)
                    
                    # Format the response
                    response = f"🔧 **Crafting Recipe: {item_name}**\n\n"
                    
                    if quantity > 1:
                        response += f"**Quantity:** {quantity}\n\n"
                    
                    # Add recipe details
                    response += f"**Direct Recipe:**\n"
                    response += f"• **Station:** {recipe_info.get('station', 'Unknown')}\n"
                    
                    if 'intel_requirement' in recipe_info:
                        intel = recipe_info['intel_requirement']
                        response += f"• **Intel:** {intel.get('points', 0)} points"
                        if intel.get('total_spent', 0) > 0:
                            response += f" ({intel['total_spent']} total required)\n"
                        else:
                            response += "\n"
                    
                    if recipe_info.get('ingredients'):
                        response += f"• **Ingredients:** {', '.join([f'{qty}x {item}' for item, qty in recipe_info['ingredients'].items()])}\n\n"
                    
                    # Add crafting tree breakdown
                    response += f"**Crafting Tree:**\n"
                    response += format_materials_tree(item_name, quantity)
                    
                    if 'description' in recipe_info:
                        response += f"\n**Description:** {recipe_info['description']}"
                    
                    return response
                    
                except Exception as crafting_error:
                    return f"❌ **Crafting Error:** {str(crafting_error)}"
            
            else:
                return f"❌ **Could not parse crafting request:** {query}\n\nExample: `@bot craft: sandbike mk3 with boost`"
            
        except Exception as e:
            return f"Error processing crafting request: {str(e)}"
    
    async def _handle_crafting_list(self) -> str:
        """Handle crafting list/categories requests"""
        try:
            # Import crafting functions to get categories
            from dune_crafting import get_categories
            
            response = "🔧 **Dune Awakening Crafting Database**\n\n"
            response += "**📊 Database Stats:**\n"
            response += "• Total Recipes: 232\n"
            response += "• Weapons: ~50 (all tiers + unique variants)\n"
            response += "• Vehicles: ~150 (sandbikes, buggies, ornithopters, sandcrawlers)\n"
            response += "• Tools: ~7 (construction, gathering, cartography)\n"
            response += "• Components: ~25 (materials, parts)\n\n"
            
            response += "**🏗️ Main Categories:**\n"
            response += "• **Weapons**: `craft: karpov 38 mk6`, `craft: maula pistol steel`\n"
            response += "• **Vehicles**: `craft: sandbike mk3`, `craft: scout ornithopter mk5`\n"
            response += "• **Tools**: `craft: cutteray mk6`, `craft: construction tool`\n\n"
            
            response += "**🚗 Vehicle Types:**\n"
            response += "• **Sandbikes**: Mk1-6 (with boost/storage options)\n"
            response += "• **Buggies**: Mk3-6 (complex rear/utility systems)\n"
            response += "• **Scout Ornithopters**: Mk4-6 (4 wings, optional modules)\n"
            response += "• **Assault Ornithopters**: Mk5-6 (6 wings, competing modules)\n"
            response += "• **Carrier Ornithopters**: Mk6 only (8 wings, heavy duty)\n"
            response += "• **Sandcrawlers**: Mk6 only (spice collection, 2 treads)\n\n"
            
            response += "**⚔️ Weapon Tiers:**\n"
            response += "• Salvage, Copper, Iron, Steel, Aluminum, Duraluminum, Plastanium\n\n"
            
            response += "**🔍 Example Queries:**\n"
            response += "• `craft: sandbike mk3 with night rider boost mk6`\n"
            response += "• `craft: assault ornithopter mk5 with rocket launcher`\n"
            response += "• `craft: karpov 38 plastanium`\n"
            response += "• `craft: cutteray mk6`\n\n"
            
            response += "**💡 Usage Tips:**\n"
            response += "• Use `craft:` or `cr:` as shortcuts\n"
            response += "• Include tier (mk1-mk6) and variant details\n"
            response += "• Get complete materials list including sub-components\n"
            response += "• Intel requirements and crafting stations included\n"
            
            return response
            
        except Exception as e:
            return f"Error generating crafting list: {str(e)}"
    
    async def _handle_crafting_category_list(self, category: str) -> str:
        """Handle category-specific list requests"""
        try:
            if category == 'weapons':
                response = "⚔️ **Weapon Categories**\n\n"
                response += "**Rifle Series:**\n"
                response += "• Karpov 38 (Salvage → Plastanium)\n"
                response += "• JABAL Spitdart (Salvage → Plastanium)\n\n"
                
                response += "**Sidearm Series:**\n"
                response += "• Maula Pistol (Salvage → Plastanium)\n"
                response += "• Disruptor M11 (Salvage → Plastanium)\n\n"
                
                response += "**Scattergun Series:**\n"
                response += "• Drillshot FK7 (Salvage → Plastanium)\n"
                response += "• GRDA 44 (Salvage → Plastanium)\n\n"
                
                response += "**Melee Weapons:**\n"
                response += "• Sword/Rapier (Long Blades)\n"
                response += "• Dirk/Kindjal (Short Blades)\n\n"
                
                response += "**Example:** `craft: karpov 38 plastanium`\n"
                
            elif category == 'vehicles':
                response = "🚗 **Vehicle Categories**\n\n"
                response += "**Ground Vehicles:**\n"
                response += "• Sandbike Mk1-6 (3 treads, boost/storage options)\n"
                response += "• Buggy Mk3-6 (4 treads, rear/utility systems)\n"
                response += "• Sandcrawler Mk6 (spice collection, 2 treads)\n\n"
                
                response += "**Flying Vehicles:**\n"
                response += "• Scout Ornithopter Mk4-6 (4 wings, optional modules)\n"
                response += "• Assault Ornithopter Mk5-6 (6 wings, competing modules)\n"
                response += "• Carrier Ornithopter Mk6 (8 wings, heavy duty)\n\n"
                
                response += "**Unique Variants:**\n"
                response += "• Night Rider Sandbike Boost\n"
                response += "• Mohandis Sandbike Engine\n"
                response += "• Walker Sandcrawler Engine\n\n"
                
                response += "**Example:** `craft: sandbike mk3 with night rider boost mk6`\n"
                
            elif category == 'tools':
                response = "🔧 **Tool Categories**\n\n"
                response += "**Construction Tools:**\n"
                response += "• Construction Tool (20x Salvaged Metal)\n"
                response += "• Staking Unit (15x Steel Ingot + 15,000 Solari)\n\n"
                
                response += "**Gathering Tools:**\n"
                response += "• Cutteray Mk6 (high-tier mining tool)\n\n"
                
                response += "**Cartography Tools:**\n"
                response += "• Survey Probe (1x Copper Ingot)\n"
                response += "• Survey Probe Launcher (2x Copper + 1x EMF Generator)\n"
                response += "• Handheld Resource Scanner (9x Iron + 6x EMF Generator)\n"
                response += "• Binoculars (15x Salvaged Metal)\n\n"
                
                response += "**Example:** `craft: cutteray mk6`\n"
            
            else:
                response = "Unknown category. Available: weapons, vehicles, tools"
            
            return response
            
        except Exception as e:
            return f"Error generating category list: {str(e)}"
    
    async def _handle_vehicle_assembly_request(self, assembly_request: str, quantity: int, original_query: str) -> str:
        """Handle vehicle assembly requests by providing parts breakdown"""
        try:
            # Parse the assembly request: VEHICLE_ASSEMBLY|vehicle_type|tier|modules
            parts = assembly_request.split('|')
            if len(parts) != 4:
                return f"❌ **Invalid vehicle assembly format:** {assembly_request}"
            
            _, vehicle_type, tier, modules = parts
            
            # Import crafting functions
            from dune_crafting import get_recipe_info, calculate_materials, list_craftable_items
            
            # Map vehicle types and get required parts
            vehicle_parts_map = {
                "assault_ornithopter": {
                    "required": ["cabin", "chassis", "cockpit", "engine", "generator", "tail", "wing"],
                    "optional_competing": ["storage", "rocket_launcher"], 
                    "optional_standalone": ["thruster"],
                    "wing_count": 6,
                    "description": "Assault Ornithopter - 6-wing combat vehicle"
                },
                "scout_ornithopter": {
                    "required": ["chassis", "cockpit", "engine", "generator", "tail", "wing"],
                    "optional": ["storage"],
                    "wing_count": 4,
                    "description": "Scout Ornithopter - 4-wing reconnaissance vehicle"
                },
                "carrier_ornithopter": {
                    "required": ["chassis", "engine", "generator", "main_hull", "side_hull", "tail_hull", "wing"],
                    "optional": ["thruster"],
                    "wing_count": 8,
                    "description": "Carrier Ornithopter - 8-wing heavy transport"
                },
                "sandbike": {
                    "required": ["chassis", "hull", "psu", "tread", "engine"],
                    "optional_mk1": ["backseat"],
                    "optional_mk2plus": ["booster", "storage"],
                    "description": "Sandbike - Fast ground vehicle"
                },
                "buggy": {
                    "required": ["engine", "chassis", "psu", "tread"],
                    "rear_choice": ["buggy_rear", "utility_rear"],
                    "optional_with_rear": ["booster"],
                    "optional_with_utility": ["cutteray", "storage"],
                    "description": "Buggy - Heavy ground vehicle"
                },
                "sandcrawler": {
                    "required": ["chassis", "engine", "cabin", "tread", "vacuum", "centrifuge", "psu"],
                    "variants": ["walker_engine", "dampened_treads"],
                    "description": "Sandcrawler - Spice harvesting vehicle"
                }
            }
            
            if vehicle_type not in vehicle_parts_map:
                return f"❌ **Unknown vehicle type:** {vehicle_type}\n\nSupported vehicles: {', '.join(vehicle_parts_map.keys())}"
            
            vehicle_info = vehicle_parts_map[vehicle_type]
            
            # Build response
            response = f"🚗 **Vehicle Assembly: {vehicle_info['description']} {tier.upper()}**\n\n"
            
            if quantity > 1:
                response += f"**Quantity:** {quantity} vehicles\n\n"
            
            response += f"**Required Parts:**\n"
            
            # Calculate total materials for all required parts
            total_materials = {}
            parts_list = []
            missing_parts = []
            
            for part in vehicle_info["required"]:
                part_key = f"{vehicle_type}_{part}_{tier.lower()}"
                
                # Special handling for wings
                if part == "wing" and "wing_count" in vehicle_info:
                    wing_count = vehicle_info["wing_count"]
                    part_quantity = wing_count * quantity
                    parts_list.append(f"• {wing_count}x {part_key} (per vehicle)")
                else:
                    part_quantity = quantity
                    parts_list.append(f"• 1x {part_key}")
                
                # Try to get recipe info and calculate materials
                recipe_info = get_recipe_info(part_key)
                if recipe_info:
                    part_materials = calculate_materials(part_key, part_quantity)
                    # Check if calculate_materials returned a dict (success) or tuple (error)
                    if isinstance(part_materials, dict):
                        for material, amount in part_materials.items():
                            total_materials[material] = total_materials.get(material, 0) + amount
                    else:
                        print(f"DEBUG: calculate_materials failed for {part_key}, returned: {part_materials}")
                        missing_parts.append(part_key)
                else:
                    print(f"DEBUG: No recipe found for part: {part_key}")
                    missing_parts.append(part_key)
            
            response += "\n".join(parts_list)
            
            # Add optional parts info
            if "optional_competing" in vehicle_info:
                response += f"\n\n**Optional (Choose One):**\n"
                for part in vehicle_info["optional_competing"]:
                    part_key = f"{vehicle_type}_{part}_{tier.lower()}"
                    response += f"• 1x {part_key}\n"
            
            if "optional_standalone" in vehicle_info:
                response += f"\n**Optional (Standalone):**\n"
                for part in vehicle_info["optional_standalone"]:
                    part_key = f"{vehicle_type}_{part}_{tier.lower()}"
                    response += f"• 1x {part_key}\n"
            
            # Add materials summary if we found any
            if total_materials:
                response += f"\n\n**Total Base Materials (Required Parts Only):**\n"
                for material, amount in sorted(total_materials.items()):
                    response += f"• {amount}x {material}\n"
            else:
                response += f"\n\n**Note:** No material calculations available (recipes not found for parts)"
            
            # Warn about missing parts
            if missing_parts:
                response += f"\n\n⚠️ **Missing Recipes:** {len(missing_parts)} parts don't have recipes in database:\n"
                for part in missing_parts[:5]:  # Show first 5
                    response += f"• {part}\n"
                if len(missing_parts) > 5:
                    response += f"• ... and {len(missing_parts) - 5} more\n"
            
            response += f"\n**Note:** Use individual part names for detailed recipes (e.g., `@bot craft: {vehicle_type}_engine_{tier.lower()}`)"
            
            return response
            
        except Exception as e:
            return f"❌ **Error processing vehicle assembly:** {str(e)}\n\n**Original request:** {original_query}"
    
    async def _build_groq_context(self, message, query: str) -> str:
        """Build context for Groq queries"""
        user_key = data_manager.get_user_key(message.author)
        user_settings = data_manager.get_user_settings(user_key)
        
        # Get conversation context
        conversation_context = self.context_manager.get_conversation_context(
            message.author.id, message.channel.id
        )
        
        # Add channel context if no conversation and enabled
        if not conversation_context and user_settings.get("use_channel_context", True):
            channel_context = await self._get_channel_context(message.channel)
            if channel_context:
                conversation_context = [{"role": "system", "content": channel_context}]
        
        # Build full context
        return await self.context_manager.build_full_context(
            query, message.author.id, message.channel.id,
            message.author.display_name, message
        )
    
    def _build_groq_system_message(self, context: str, user_id: int) -> str:
        """Build system message for Groq"""
        parts = []
        
        if context:
            parts.append(f"RELEVANT CONTEXT:\\n{context}")
            parts.append("=" * 50)
        
        core_instructions = """You are a helpful AI assistant with the following capabilities:

1. **General Knowledge**: Answer questions using your training data and any relevant context provided above.

2. **Discord Server Management** (Admin only): Help with server administration including user moderation, role management, channel management, and message cleanup.

The relevant context section above contains only information pertinent to the current query. Use this context to provide more personalized and informed responses."""

        parts.append(core_instructions)
        
        # Add admin capabilities if user is admin
        if is_admin(user_id):
            admin_instructions = """Additional admin capabilities:

- User moderation (kick, ban, timeout/mute users)
- Role management (add/remove roles from users, rename roles)  
- Channel management (create/delete channels)
- Message cleanup (bulk delete messages, including from specific users)
- Nickname changes

When you detect an administrative request, respond by clearly stating what action you understood. DO NOT ask for text-based confirmation. The system will automatically handle confirmation.

Use this format:
I understand you want to [ACTION]. [Brief description of what will happen]

Examples:
- "kick that spammer" → I understand you want to kick [user]. They will be removed from the server.
- "delete John's messages" → I understand you want to delete messages from John. I'll remove their recent messages.
- "rename role Moderator to Super Mod" → I understand you want to rename the Moderator role to Super Mod.

Be concise and clear about what the action will do."""

            parts.append(admin_instructions)
        
        return "\\n\\n".join(parts)
    
    async def _handle_admin_actions(self, message, query: str, response: str) -> bool:
        """Handle admin action detection and confirmation"""
        if not is_admin(message.author.id) or not message.guild:
            return False
        
        if message.author.id in self.pending_admin_actions:
            return False
        
        # Parse admin intent
        action_type, parameters = await self.intent_parser.parse_admin_intent(
            query, message.guild, message.author
        )
        
        if not action_type:
            return False
        
        self._cleanup_stale_admin_actions()
        
        # Store pending action
        self.pending_admin_actions[message.author.id] = {
            "action_type": action_type,
            "parameters": parameters,
            "message_id": message.id,
            "original_message": message,
            "timestamp": datetime.now()
        }
        
        print(f"DEBUG: Admin action detected: {action_type}")
        
        # Add confirmation to response
        if not any(keyword in response for keyword in ["Admin Action", "React with", "✅", "❌"]):
            response += f"\\n\\n[ADMIN] Action detected: {action_type}\\nReact with ✅ to proceed or ❌ to cancel."
        
        # Send message with reactions
        sent_msg = await message.channel.send(response)
        await sent_msg.add_reaction('✅')
        await sent_msg.add_reaction('❌')
        
        # Store confirmation message
        self.pending_admin_actions[message.author.id]["confirmation_message"] = sent_msg
        
        return True
    
    async def handle_admin_confirmation(self, reaction, user):
        """Handle admin reaction confirmations"""
        if user.bot or not is_admin(user.id):
            return
        
        # Find matching pending action
        for admin_user_id, action_data in self.pending_admin_actions.items():
            if (admin_user_id == user.id and 
                "confirmation_message" in action_data and 
                reaction.message.id == action_data["confirmation_message"].id):
                
                emoji = str(reaction.emoji)
                
                if emoji == '✅':
                    # Execute admin action
                    action_data = self.pending_admin_actions.pop(admin_user_id)
                    original_message = action_data.get("original_message", reaction.message)
                    
                    admin_response = await self.admin_handler.execute_admin_action(
                        original_message, action_data["action_type"], action_data["parameters"]
                    )
                    
                    await reaction.message.channel.send(admin_response)
                    
                elif emoji == '❌':
                    # Cancel admin action
                    self.pending_admin_actions.pop(admin_user_id, None)
                    await reaction.message.channel.send("❌ **Admin action cancelled.**")
                
                # Clear reactions
                try:
                    await reaction.message.clear_reactions()
                except:
                    pass
                
                break
    
    async def _perform_google_search(self, query: str) -> str:
        """Perform Google search"""
        try:
            if not config.has_google_search():
                return "Google search not configured"
            
            # Import here to avoid circular imports
            from googleapiclient.discovery import build
            
            service = build("customsearch", "v1", developerKey=config.GOOGLE_API_KEY)
            result = service.cse().list(q=query, cx=config.GOOGLE_SEARCH_ENGINE_ID, num=10).execute()
            
            if 'items' not in result:
                return f"No search results found for: {query}"
            
            search_results = f"Current web search results for '{query}':\\n\\n"
            
            for i, item in enumerate(result['items'][:10], 1):
                title = item['title']
                link = item['link']
                snippet = item.get('snippet', 'No description available')
                
                search_results += f"{i}. **{title}**\\n"
                search_results += f"   {snippet[:400]}...\\n"
                search_results += f"   Source: <{link}>\\n\\n"
            
            return search_results
        
        except Exception as e:
            return f"Search failed: {str(e)}"
    
    def _suppress_link_previews(self, text: str) -> str:
        """Wrap URLs in angle brackets to suppress Discord previews"""
        import re
        url_pattern = r'(?<!\\<)(https?://[^\\s\\>]+)(?!\\>)'
        return re.sub(url_pattern, r'<\\1>', text)
    
    async def _get_channel_context(self, channel, limit: int = None) -> str:
        """Get recent channel messages for context"""
        if limit is None:
            limit = config.CHANNEL_CONTEXT_LIMIT
        
        try:
            messages = []
            async for message in channel.history(limit=limit, oldest_first=False):
                if message.author.bot:
                    continue
                
                content = f"{message.author.display_name}: {message.content}"
                messages.append(content)
            
            messages.reverse()
            
            if messages:
                display_limit = config.CHANNEL_CONTEXT_DISPLAY
                return "Recent channel messages:\\n" + "\\n".join(messages[-display_limit:])
            return ""
        except Exception as e:
            print(f"Error fetching channel context: {e}")
            return ""
    
    async def _handle_rate_limit(self, message):
        """Handle rate limited users"""
        reset_time = self.rate_limiter.get_reset_time(message.author.id)
        wait_seconds = int((reset_time - datetime.now()).total_seconds()) if reset_time else 60
        await message.channel.send(
            f'⏰ **Rate Limited**: Please wait {wait_seconds} seconds before making another AI request.'
        )
    
    async def _send_response(self, message, response: str):
        """Send response with smart message splitting"""
        if not response:
            return
        
        message_chunks = smart_split_message(response)
        for chunk in message_chunks:
            await message.channel.send(chunk)