"""
Reddit API client for authenticated access
Handles OAuth2 authentication and API requests
"""

import aiohttp
import asyncio
import base64
import time
from typing import Optional, Dict, Any
from ..config import config
from ..utils.logging import get_logger

logger = get_logger(__name__)


class RedditClient:
    """Authenticated Reddit API client"""
    
    def __init__(self):
        self.access_token: Optional[str] = None
        self.token_expires_at: float = 0
        self.base_url = "https://oauth.reddit.com"
        self.auth_url = "https://www.reddit.com/api/v1/access_token"
        
    async def _get_access_token(self, session: aiohttp.ClientSession) -> bool:
        """Get OAuth2 access token from Reddit"""
        try:
            if not config.has_reddit_api():
                logger.error("Reddit API credentials not configured")
                return False
            
            # Prepare authentication
            auth_string = f"{config.REDDIT_CLIENT_ID}:{config.REDDIT_CLIENT_SECRET}"
            auth_bytes = auth_string.encode('ascii')
            auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
            
            headers = {
                'Authorization': f'Basic {auth_b64}',
                'User-Agent': config.REDDIT_USER_AGENT,
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            data = {
                'grant_type': 'client_credentials'
            }
            
            async with session.post(self.auth_url, headers=headers, data=data) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Reddit auth failed: HTTP {response.status} - {error_text}")
                    return False
                
                token_data = await response.json()
                
                if 'access_token' not in token_data:
                    logger.error(f"No access token in response: {token_data}")
                    return False
                
                self.access_token = token_data['access_token']
                expires_in = token_data.get('expires_in', 3600)  # Default 1 hour
                self.token_expires_at = time.time() + expires_in - 60  # Refresh 1 minute early
                
                logger.info("Reddit API authentication successful")
                return True
                
        except Exception as e:
            logger.error(f"Reddit authentication error: {e}")
            return False
    
    async def _ensure_authenticated(self, session: aiohttp.ClientSession) -> bool:
        """Ensure we have a valid access token"""
        if not self.access_token or time.time() >= self.token_expires_at:
            return await self._get_access_token(session)
        return True
    
    async def get_post_data(self, session: aiohttp.ClientSession, post_url: str) -> Optional[Dict[str, Any]]:
        """Get Reddit post data using authenticated API"""
        try:
            if not await self._ensure_authenticated(session):
                return None
            
            # Extract post info from URL
            # Example: https://www.reddit.com/r/manga/comments/1497vwl/actually_well_written_romance_mangas/
            if '/comments/' not in post_url:
                logger.error(f"Invalid Reddit post URL format: {post_url}")
                return None
            
            # Convert to API endpoint
            # Remove domain and convert to API path
            url_parts = post_url.split('/comments/')
            if len(url_parts) != 2:
                return None
            
            subreddit_part = url_parts[0].split('/r/')[-1]  # Extract subreddit
            post_id = url_parts[1].split('/')[0]  # Extract post ID
            
            api_url = f"{self.base_url}/r/{subreddit_part}/comments/{post_id}"
            
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'User-Agent': config.REDDIT_USER_AGENT
            }
            
            async with session.get(api_url, headers=headers) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Reddit API request failed: HTTP {response.status} - {error_text}")
                    return None
                
                data = await response.json()
                return data
                
        except Exception as e:
            logger.error(f"Reddit API request error: {e}")
            return None
    
    async def extract_content_from_data(self, data: Dict[str, Any]) -> Optional[Dict[str, str]]:
        """Extract readable content from Reddit API response"""
        try:
            if not isinstance(data, list) or len(data) == 0:
                return None
            
            # Post data is in first element
            post_listing = data[0]
            if 'data' not in post_listing or 'children' not in post_listing['data']:
                return None
            
            post_data = post_listing['data']['children'][0]['data']
            
            # Comments data is in second element (if available)
            comments_data = []
            if len(data) > 1 and 'data' in data[1] and 'children' in data[1]['data']:
                comments_data = data[1]['data']['children']
            
            # Extract post information
            title = post_data.get('title', 'No title')
            selftext = post_data.get('selftext', '')
            author = post_data.get('author', 'Unknown')
            subreddit = post_data.get('subreddit', 'Unknown')
            score = post_data.get('score', 0)
            num_comments = post_data.get('num_comments', 0)
            created_utc = post_data.get('created_utc', 0)
            
            # Build content
            content_parts = [f"**{title}**"]
            content_parts.append(f"*Posted by u/{author} in r/{subreddit} • {score} upvotes • {num_comments} comments*")
            
            if selftext and selftext.strip():
                content_parts.append(f"\n**Post Content:**\n{selftext}")
            
            # Add top comments
            if comments_data:
                content_parts.append(f"\n**Top Comments:**")
                comment_count = 0
                
                for comment_item in comments_data[:10]:  # Check up to 10 comments
                    if comment_item.get('kind') != 't1':  # Skip non-comments
                        continue
                    
                    comment = comment_item.get('data', {})
                    comment_body = comment.get('body', '')
                    comment_author = comment.get('author', 'Unknown')
                    comment_score = comment.get('score', 0)
                    
                    # Skip removed/deleted comments
                    if not comment_body or comment_body in ['[removed]', '[deleted]']:
                        continue
                    
                    # Add comment (truncate if too long)
                    if len(comment_body) > 300:
                        comment_body = comment_body[:300] + "..."
                    
                    content_parts.append(f"\n• u/{comment_author} ({comment_score} points): {comment_body}")
                    comment_count += 1
                    
                    if comment_count >= 5:  # Limit to top 5 comments
                        break
            
            full_content = '\n'.join(content_parts)
            
            return {
                'url': post_data.get('url', ''),
                'title': title,
                'content': full_content,
                'length': len(full_content)
            }
            
        except Exception as e:
            logger.error(f"Error extracting Reddit content: {e}")
            return None