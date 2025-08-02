"""
Perplexity AI Integration
Provides web search capabilities with conversation context storage.
"""

import aiohttp
import json
from typing import Dict, List, Optional
from collections import defaultdict, deque
from datetime import datetime, timedelta
from ..config import config

class PerplexitySearch:
    """Perplexity AI search integration with built-in web search and conversation context"""
    
    def __init__(self):
        self.base_url = "https://api.perplexity.ai/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {config.PERPLEXITY_API_KEY}",
            "Content-Type": "application/json"
        }
        self.timeout = aiohttp.ClientTimeout(total=30)
        
        # Store conversation context per user/channel
        self.conversation_contexts: Dict[str, deque] = defaultdict(lambda: deque(maxlen=10))
        self.last_activity: Dict[str, datetime] = {}
        
        # Context expiry time (30 minutes)
        self.context_expiry = timedelta(minutes=30)
    
    def _get_context_key(self, user_id: int, channel_id: int) -> str:
        """Generate a unique key for user+channel context"""
        return f"{user_id}_{channel_id}"
    
    def _cleanup_expired_contexts(self):
        """Remove expired conversation contexts"""
        current_time = datetime.now()
        expired_keys = [
            key for key, last_time in self.last_activity.items()
            if current_time - last_time > self.context_expiry
        ]
        
        for key in expired_keys:
            self.conversation_contexts.pop(key, None)
            self.last_activity.pop(key, None)
    
    def _is_followup_question(self, query: str) -> bool:
        """Determine if this is likely a follow-up question"""
        followup_indicators = [
            'what about', 'and what', 'tell me more', 'more about', 'more info',
            'elaborate', 'explain', 'details', 'specifically', 'also',
            'additionally', 'furthermore', 'moreover', 'besides',
            'what else', 'anything else', 'other', 'alternative',
            'compare', 'versus', 'vs', 'difference', 'similar',
            'follow up', 'followup', 'continue', 'next', 'then',
            'expand on', 'go deeper', 'dive deeper', 'more details',
            'clarify', 'clarification', 'can you', 'could you',
            'how does', 'why does', 'what makes', 'which one',
            'that', 'this', 'it', 'they', 'them', 'those', 'these'
        ]
        
        query_lower = query.lower().strip()
        
        # Check for direct followup indicators
        if any(indicator in query_lower for indicator in followup_indicators):
            return True
        
        # Check for pronouns that might refer to previous context
        pronouns = ['that', 'this', 'it', 'they', 'them', 'those', 'these']
        query_words = query_lower.split()
        if len(query_words) <= 6 and any(pronoun in query_words for pronoun in pronouns):
            return True
        
        # Check for short questions that might be follow-ups
        if len(query_words) <= 4 and any(word in query_words for word in ['what', 'how', 'why', 'when', 'where', 'which']):
            return True
        
        return False
    
    async def search_and_answer(self, query: str, user_id: int = None, channel_id: int = None) -> str:
        """Use Perplexity to search and provide a comprehensive answer with conversation context"""
        if not config.has_perplexity_api():
            return "Perplexity API is not configured."
        
        try:
            # Clean up expired contexts
            self._cleanup_expired_contexts()
            
            # Build messages array starting with system prompt
            messages = [
                {
                    "role": "system",
                    "content": "You are a helpful assistant that provides comprehensive, accurate answers using current information from the web. Always cite your sources when possible. If the user asks follow-up questions, use the conversation context to provide more detailed or related information."
                }
            ]
            
            # Add conversation context if available and this looks like a follow-up
            context_key = None
            if user_id and channel_id:
                context_key = self._get_context_key(user_id, channel_id)
                context = self.conversation_contexts.get(context_key)
                
                if context and (self._is_followup_question(query) or len(context) > 0):
                    # Add recent conversation context
                    for msg in context:
                        messages.append(msg)
            
            # Add current user query
            messages.append({
                "role": "user", 
                "content": query
            })
            
            payload = {
                "model": "sonar",
                "messages": messages,
                "max_tokens": 1000,
                "temperature": 0.2,
                "top_p": 0.9,
                "search_domain_filter": ["perplexity.ai"],
                "return_images": False,
                "return_related_questions": False,
                "search_recency_filter": "month",
                "top_k": 0,
                "stream": False,
                "presence_penalty": 0,
                "frequency_penalty": 1
            }
            
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.post(self.base_url, headers=self.headers, json=payload) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        return f"Perplexity API error ({response.status}): {error_text}"
                    
                    result = await response.json()
                    
                    if 'choices' in result and len(result['choices']) > 0:
                        answer = result['choices'][0]['message']['content']
                        
                        # Store conversation context for future follow-ups
                        if context_key:
                            context = self.conversation_contexts[context_key]
                            
                            # Add user query and assistant response to context
                            context.append({"role": "user", "content": query})
                            context.append({"role": "assistant", "content": answer})
                            
                            # Update last activity time
                            self.last_activity[context_key] = datetime.now()
                        
                        return answer
                    else:
                        return "No response from Perplexity API."
        
        except aiohttp.ClientError as e:
            return f"Network error connecting to Perplexity: {str(e)}"
        except json.JSONDecodeError as e:
            return f"Error parsing Perplexity response: {str(e)}"
        except Exception as e:
            return f"Unexpected error with Perplexity search: {str(e)}"
    
    def clear_context(self, user_id: int, channel_id: int):
        """Clear conversation context for a specific user/channel"""
        context_key = self._get_context_key(user_id, channel_id)
        self.conversation_contexts.pop(context_key, None)
        self.last_activity.pop(context_key, None)
    
    def clear_all_contexts(self):
        """Clear all conversation contexts"""
        self.conversation_contexts.clear()
        self.last_activity.clear()
    
    def get_context_info(self, user_id: int, channel_id: int) -> dict:
        """Get information about the current context for a user/channel"""
        context_key = self._get_context_key(user_id, channel_id)
        context = self.conversation_contexts.get(context_key)
        last_activity = self.last_activity.get(context_key)
        
        return {
            "has_context": bool(context),
            "message_count": len(context) if context else 0,
            "last_activity": last_activity,
            "expires_at": last_activity + self.context_expiry if last_activity else None
        }

# Global instance
perplexity_search = PerplexitySearch()