import asyncio
import aiohttp
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import re
from typing import Optional

class WebScraper:
    """Web scraping functionality for AI integration"""
    
    def __init__(self):
        self.timeout = aiohttp.ClientTimeout(total=10)
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
    
    async def scrape_url(self, url: str) -> str:
        """Scrape content from a specific URL"""
        try:
            # Validate URL
            if not self._is_valid_url(url):
                return f"Invalid URL: {url}"
            
            async with aiohttp.ClientSession(timeout=self.timeout, headers=self.headers) as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        return f"Failed to fetch {url}: HTTP {response.status}"
                    
                    # Check content type
                    content_type = response.headers.get('content-type', '').lower()
                    if 'text/html' not in content_type:
                        return f"URL does not contain HTML content: {content_type}"
                    
                    html = await response.text()
                    
                    # Parse and extract content
                    soup = BeautifulSoup(html, 'html.parser')
                    content = self._extract_content(soup, url)
                    
                    return content
        
        except asyncio.TimeoutError:
            return f"Timeout while scraping {url}"
        except aiohttp.ClientError as e:
            return f"Network error while scraping {url}: {str(e)}"
        except Exception as e:
            return f"Error scraping {url}: {str(e)}"
    
    def _is_valid_url(self, url: str) -> bool:
        """Validate URL format and scheme"""
        try:
            parsed = urlparse(url)
            return parsed.scheme in ('http', 'https') and bool(parsed.netloc)
        except Exception:
            return False
    
    def _extract_content(self, soup: BeautifulSoup, url: str) -> str:
        """Extract meaningful content from HTML"""
        # Remove script and style elements
        for script in soup(["script", "style", "nav", "header", "footer", "aside"]):
            script.decompose()
        
        # Get title
        title = ""
        title_tag = soup.find('title')
        if title_tag:
            title = title_tag.get_text().strip()
        
        # Extract main content
        content_selectors = [
            'main', 'article', '.content', '#content', 
            '.main-content', '.post-content', '.entry-content'
        ]
        
        main_content = None
        for selector in content_selectors:
            main_content = soup.select_one(selector)
            if main_content:
                break
        
        # Fallback to body if no main content found
        if not main_content:
            main_content = soup.find('body')
        
        if not main_content:
            return f"No content found on {url}"
        
        # Extract text
        text = main_content.get_text()
        
        # Clean up text
        text = re.sub(r'\s+', ' ', text)  # Replace multiple whitespace with single space
        text = text.strip()
        
        # Limit content length
        max_length = 3000
        if len(text) > max_length:
            text = text[:max_length] + "... [Content truncated]"
        
        # Format result
        result = f"**Website: {url}**\n"
        if title:
            result += f"**Title: {title}**\n\n"
        result += f"**Content:**\n{text}"
        
        return result

# Global instance
web_scraper = WebScraper()