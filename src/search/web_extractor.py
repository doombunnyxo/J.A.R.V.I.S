"""
Web content extraction for enhanced search results
Fetches full page content and cleans it for AI processing
"""

import aiohttp
import asyncio
from typing import List, Dict, Optional
from urllib.parse import urljoin, urlparse
import re

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError as e:
    HAS_BS4 = False
    BeautifulSoup = None

class WebContentExtractor:
    """Extract and clean web page content"""
    
    def __init__(self, timeout: int = 10, max_content_length: int = 50000):
        self.timeout = timeout
        self.max_content_length = max_content_length
        self.session_timeout = aiohttp.ClientTimeout(total=timeout)
    
    async def extract_multiple_pages(self, urls: List[str], debug_channel=None) -> List[Dict[str, str]]:
        """Extract content from multiple URLs concurrently"""
        if not HAS_BS4:
            raise ImportError("BeautifulSoup4 is required for web content extraction. Install with: pip install beautifulsoup4")
        
        if debug_channel:
            url_list = '\n'.join([f"{i+1}. {url}" for i, url in enumerate(urls[:5])])  # Show first 5 URLs
            if len(urls) > 5:
                url_list += f"\n... and {len(urls)-5} more URLs"
            await debug_channel.send(f"🔧 **Debug**: Attempting to extract from URLs:\n```\n{url_list}\n```")
        
        async with aiohttp.ClientSession(timeout=self.session_timeout) as session:
            tasks = [self._extract_single_page(session, url, debug_channel) for url in urls]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Filter out exceptions and return successful extractions
            extracted_pages = []
            first_page_posted = False
            
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    error_msg = f"Failed to extract {urls[i]}: {result}"
                    print(f"DEBUG: {error_msg}")
                    if debug_channel:
                        await debug_channel.send(f"🔧 **Debug**: ❌ {error_msg}")
                    continue
                
                if result and result.get('content'):
                    extracted_pages.append(result)
                    
                    # Post first successfully extracted page to Discord for debugging
                    if not first_page_posted and debug_channel:
                        try:
                            content_preview = result['content'][:1500] + "..." if len(result['content']) > 1500 else result['content']
                            debug_msg = f"🔍 **First Scraped Page Debug**\n**URL**: {result['url']}\n**Title**: {result['title']}\n**Content ({result['length']} chars)**:\n```\n{content_preview}\n```"
                            await debug_channel.send(debug_msg)
                            first_page_posted = True
                        except Exception as e:
                            print(f"DEBUG: Failed to post scraped content to Discord: {e}")
                else:
                    # Debug why page returned no content
                    if debug_channel:
                        if result is None:
                            await debug_channel.send(f"🔧 **Debug**: ❌ URL <{urls[i]}> returned None")
                        elif not result.get('content'):
                            await debug_channel.send(f"🔧 **Debug**: ❌ URL <{urls[i]}> returned empty content - Title: {result.get('title', 'No title')}")
                        else:
                            await debug_channel.send(f"🔧 **Debug**: ❌ URL <{urls[i]}> - Unknown issue with result: {str(result)[:200]}")
            
            return extracted_pages
    
    async def _extract_single_page(self, session: aiohttp.ClientSession, url: str, debug_channel=None) -> Optional[Dict[str, str]]:
        """Extract content from a single URL"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            async with session.get(url, headers=headers) as response:
                if response.status != 200:
                    if debug_channel:
                        await debug_channel.send(f"🔧 **Debug**: ❌ <{url}> - HTTP {response.status}")
                    return None
                
                # Check content type
                content_type = response.headers.get('content-type', '').lower()
                if 'text/html' not in content_type:
                    if debug_channel:
                        await debug_channel.send(f"🔧 **Debug**: ❌ <{url}> - Not HTML content: {content_type}")
                    return None
                
                html_content = await response.text()
                if debug_channel:
                    await debug_channel.send(f"🔧 **Debug**: ✅ <{url}> - Got HTML ({len(html_content)} chars)")
                
                # Parse with BeautifulSoup
                soup = BeautifulSoup(html_content, 'html.parser')
                
                # Extract title
                title = soup.find('title')
                title_text = title.get_text().strip() if title else urlparse(url).netloc
                
                # Clean and extract content
                cleaned_content = self._clean_html_content(soup)
                
                if not cleaned_content or len(cleaned_content.strip()) < 100:
                    if debug_channel:
                        await debug_channel.send(f"🔧 **Debug**: ❌ <{url}> - Content too short ({len(cleaned_content) if cleaned_content else 0} chars) after cleaning")
                    return None
                
                # Truncate if too long
                if len(cleaned_content) > self.max_content_length:
                    cleaned_content = cleaned_content[:self.max_content_length] + "..."
                
                if debug_channel:
                    await debug_channel.send(f"🔧 **Debug**: ✅ <{url}> - Successfully extracted {len(cleaned_content)} chars")
                
                return {
                    'url': url,
                    'title': title_text,
                    'content': cleaned_content,
                    'length': len(cleaned_content)
                }
                
        except Exception as e:
            error_msg = f"Error extracting {url}: {e}"
            print(f"DEBUG: {error_msg}")
            if debug_channel:
                await debug_channel.send(f"🔧 **Debug**: ❌ <{url}> - Exception: {str(e)}")
            return None
    
    def _clean_html_content(self, soup: BeautifulSoup) -> str:
        """Clean HTML content by removing unwanted elements and extracting text"""
        
        # Remove unwanted elements
        unwanted_tags = [
            'script', 'style', 'nav', 'header', 'footer', 'aside', 
            'advertisement', 'ads', 'sidebar', 'menu', 'breadcrumb',
            'social-share', 'comments', 'related', 'recommended'
        ]
        
        for tag in unwanted_tags:
            for element in soup.find_all(tag):
                element.decompose()
        
        # Remove elements by class/id patterns (common ad/navigation patterns)
        unwanted_patterns = [
            'ad', 'ads', 'advertisement', 'sponsor', 'promo',
            'nav', 'menu', 'sidebar', 'footer', 'header',
            'social', 'share', 'comment', 'related', 'recommend'
        ]
        
        for pattern in unwanted_patterns:
            # Remove by class
            for element in soup.find_all(class_=re.compile(pattern, re.I)):
                element.decompose()
            # Remove by id
            for element in soup.find_all(id=re.compile(pattern, re.I)):
                element.decompose()
        
        # Focus on main content areas
        main_content = None
        content_selectors = [
            'main', 'article', '[role="main"]', '.main-content', 
            '.article-content', '.post-content', '.entry-content',
            '.content', '#content', '#main'
        ]
        
        for selector in content_selectors:
            element = soup.select_one(selector)
            if element:
                main_content = element
                break
        
        # If no main content found, use body
        if not main_content:
            main_content = soup.find('body') or soup
        
        # Extract text with proper spacing
        text_content = self._extract_text_with_structure(main_content)
        
        # Clean up the text
        text_content = self._clean_extracted_text(text_content)
        
        return text_content
    
    def _extract_text_with_structure(self, element) -> str:
        """Extract text while preserving some structure"""
        text_parts = []
        
        # Check if element has children attribute (some BeautifulSoup objects don't)
        if not hasattr(element, 'children'):
            # If it's a text node, return its string representation
            text = str(element).strip()
            return text if len(text) > 10 else ""
        
        try:
            for child in element.children:
                # Skip comments, doctypes, and other non-element nodes
                if hasattr(child, 'name') and child.name:
                    if child.name in ['p', 'div', 'article', 'section']:
                        text = child.get_text().strip()
                        if text and len(text) > 20:  # Only include substantial paragraphs
                            text_parts.append(text)
                    elif child.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                        text = child.get_text().strip()
                        if text:
                            text_parts.append(f"\n## {text}\n")
                    elif child.name in ['ul', 'ol']:
                        # Handle lists
                        list_items = child.find_all('li')
                        for li in list_items:
                            li_text = li.get_text().strip()
                            if li_text:
                                text_parts.append(f"• {li_text}")
                    else:
                        # Recursively process other elements
                        nested_text = self._extract_text_with_structure(child)
                        if nested_text:
                            text_parts.append(nested_text)
                elif str(child).strip():
                    # Text node - but check if it's substantial
                    text = str(child).strip()
                    if text and len(text) > 10 and not text.startswith('<!--'):
                        text_parts.append(text)
        except Exception as e:
            # If iteration fails, fall back to simple text extraction
            if hasattr(element, 'get_text'):
                return element.get_text().strip()
            else:
                return str(element).strip()
        
        return "\n".join(text_parts)
    
    def _clean_extracted_text(self, text: str) -> str:
        """Clean up extracted text"""
        if not text:
            return ""
        
        # Remove excessive whitespace
        text = re.sub(r'\n\s*\n\s*\n', '\n\n', text)  # Multiple newlines to double
        text = re.sub(r' +', ' ', text)  # Multiple spaces to single
        
        # Remove common junk patterns
        junk_patterns = [
            r'Accept cookies?.*?Reject',
            r'This website uses cookies.*?Accept',
            r'Subscribe to our newsletter.*?Sign up',
            r'Follow us on.*?Twitter',
            r'Share this.*?Facebook',
            r'Advertisement',
            r'Sponsored content'
        ]
        
        for pattern in junk_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE | re.DOTALL)
        
        # Remove very short lines (likely navigation/junk)
        lines = text.split('\n')
        meaningful_lines = []
        for line in lines:
            line = line.strip()
            if len(line) > 15 or line.startswith('##'):  # Keep headings and substantial content
                meaningful_lines.append(line)
        
        return '\n'.join(meaningful_lines).strip()