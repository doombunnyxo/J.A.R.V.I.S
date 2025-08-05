"""
Web content extraction for enhanced search results
Fetches full page content and cleans it for AI processing
"""

import aiohttp
import asyncio
from typing import List, Dict, Optional
from urllib.parse import urljoin, urlparse
import re
import json

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError as e:
    HAS_BS4 = False
    BeautifulSoup = None

class WebContentExtractor:
    """Extract and clean web page content"""
    
    def __init__(self, timeout: int = 8, max_content_length: int = 50000):
        self.timeout = timeout
        self.max_content_length = max_content_length
        self.session_timeout = aiohttp.ClientTimeout(total=timeout)
    
    async def extract_multiple_pages(self, urls: List[str], debug_channel=None) -> List[Dict[str, str]]:
        """Extract content from multiple URLs concurrently"""
        # Debug: Show we entered the extractor
        if debug_channel:
            try:
                await debug_channel.send(f"🚀 **EXTRACTOR STARTED**: Processing {len(urls)} URLs")
            except Exception as e:
                print(f"DEBUG: Failed to send extractor start message: {e}")
        
        if not HAS_BS4:
            raise ImportError("BeautifulSoup4 is required for web content extraction. Install with: pip install beautifulsoup4")
        
        # Filter out blocked domains
        from .domain_filter import get_domain_filter
        domain_filter = get_domain_filter()
        
        allowed_urls, blocked_urls = domain_filter.filter_urls(urls)
        
        if not allowed_urls:
            return []
        
        # Create session with timeouts allowing for slow site detection
        timeout = aiohttp.ClientTimeout(
            total=self.timeout,     # 8s total per request
            connect=2,              # 2s to establish connection
            sock_read=6             # 6s to read response
        )
        
        async with aiohttp.ClientSession(timeout=timeout) as session:
            # Progressive timeout approach - collect results as they complete
            tasks = [self._extract_single_page(session, url) for url in allowed_urls]
            extracted_pages = []
            failed_sites = []  # Collect failures for batch processing later
            slow_sites = []    # Collect slow sites for batch processing later
            
            # Collect results as they complete, with count-based exit and slow site tracking
            estimated_summary_tokens = 0
            target_summary_tokens = 3000  # Target ~3000 tokens from summaries
            max_timeout = 6.0  # 6 seconds to identify slow sites
            
            # Wait for results to complete
            pending_tasks = set(tasks)
            timeout_start = asyncio.get_event_loop().time()
            url_by_task = {task: url for task, url in zip(tasks, allowed_urls)}  # Track which URL belongs to which task
            
            marked_slow_at_6s = False  # Track if we've already marked slow sites
            
            # Debug to Discord
            if debug_channel:
                try:
                    await debug_channel.send(f"🔍 **Web Extraction Started**: {len(allowed_urls)} URLs, target: {target_summary_tokens} tokens")
                except: pass
            
            max_total_time = 8.0  # Maximum 8 seconds total for web extraction
            
            while pending_tasks and estimated_summary_tokens < target_summary_tokens:
                # Debug: Show we're in the loop
                if debug_channel and len(extracted_pages) == 0:  # Only on first iteration
                    try:
                        await debug_channel.send(f"🔁 **ENTERED MAIN LOOP**: {len(pending_tasks)} tasks pending")
                    except: pass
                
                # Check total elapsed time
                total_elapsed = asyncio.get_event_loop().time() - timeout_start
                if total_elapsed >= max_total_time:
                    print(f"DEBUG: Hitting 8s total time limit with {len(pending_tasks)} tasks remaining - exiting extraction")
                    if debug_channel:
                        try:
                            await debug_channel.send(f"⏰ **WEB EXTRACTION TIMEOUT**: Hit 8s limit, stopping with {len(extracted_pages)} pages")
                        except: pass
                    break
                # Check if we've hit the 6 second mark to identify slow sites (but don't exit)
                elapsed = asyncio.get_event_loop().time() - timeout_start
                if elapsed >= max_timeout and not marked_slow_at_6s:
                    print(f"DEBUG: Hit 6s mark - adding {len(pending_tasks)} remaining sites to slow list (but continuing to wait)")
                    # Add remaining sites to slow list (they're taking >6s) but keep waiting
                    for task in pending_tasks:
                        url = url_by_task.get(task, 'unknown')
                        if url != 'unknown':
                            slow_sites.append((url, elapsed))  # Use elapsed time as response time
                    marked_slow_at_6s = True  # Don't mark again
                
                # Wait for next completion - use full request timeout
                wait_timeout = 8.0  # Wait up to 8 seconds for any task to complete
                
                # Debug: About to wait
                if debug_channel and len(extracted_pages) < 2:  # Limit spam
                    try:
                        await debug_channel.send(f"🕐 **ABOUT TO WAIT**: {len(pending_tasks)} tasks, timeout: {wait_timeout:.1f}s")
                    except: pass
                
                try:
                    done, pending_tasks = await asyncio.wait(
                        pending_tasks, 
                        timeout=wait_timeout,
                        return_when=asyncio.FIRST_COMPLETED
                    )
                    
                    # Debug: Show wait results
                    if debug_channel and (len(done) > 0 or len(extracted_pages) < 3):  # Limit spam
                        try:
                            await debug_channel.send(f"⏱️ **WAIT RESULT**: {len(done)} completed, {len(pending_tasks)} pending, timeout: {wait_timeout:.1f}s")
                        except: pass
                    
                    # Process completed results
                    for task in done:
                        try:
                            result = await task
                            if result and result.get('content'):
                                extracted_pages.append(result)
                                
                                # Estimate actual summary tokens based on content length
                                # Summaries are capped at 300 tokens, but might be shorter for brief content
                                content_length = len(result['content'])
                                content_tokens = content_length // 4  # Rough token estimate
                                expected_summary_tokens = min(content_tokens // 3, 300)  # Summaries are ~1/3 of original content, capped at 300
                                
                                estimated_summary_tokens += expected_summary_tokens
                                print(f"DEBUG: Got page {len(extracted_pages)}, content: {content_length} chars, estimated summary: {expected_summary_tokens} tokens (total: {estimated_summary_tokens})")
                                
                                # Track slow sites (>3s response time) 
                                if result.get('response_time', 0) > 3.0:
                                    slow_sites.append((result['url'], result['response_time']))
                            else:
                                # Track failed extractions
                                failed_sites.append(('unknown', 'extraction_failed'))
                        except Exception as e:
                            # Track exceptions
                            failed_sites.append(('unknown', str(e)))
                
                except asyncio.TimeoutError:
                    continue
            
            # Debug: Show we exited the main loop
            if debug_channel:
                try:
                    await debug_channel.send(f"🔄 **EXITED MAIN LOOP**: {len(extracted_pages)} pages, {len(pending_tasks)} remaining tasks")
                except: pass
            
            # Handle remaining tasks - either cancelled due to timeout or still pending
            if pending_tasks:
                print(f"DEBUG: Handling remaining {len(pending_tasks)} tasks")
                # Cancel remaining tasks to prevent RuntimeWarning
                for task in pending_tasks:
                    if not task.done():
                        task.cancel()
                
                # Gather results including cancelled ones
                remaining_results = await asyncio.gather(*pending_tasks, return_exceptions=True)
                
                # Process remaining results
                for result in remaining_results:
                    if isinstance(result, Exception):
                        failed_sites.append(('unknown', str(result)))
                        continue
                    
                    if result and result.get('content'):
                        extracted_pages.append(result)
                        # These were already marked as slow if they took >6s
                        if result.get('response_time', 0) > 3.0:
                            slow_sites.append((result['url'], result['response_time']))
                    else:
                        failed_sites.append(('unknown', 'extraction_failed'))
            
            print(f"DEBUG: Stopped at {len(extracted_pages)} pages, ~{estimated_summary_tokens} summary tokens")
                
            print(f"DEBUG: Web extraction completed with {len(extracted_pages)} successful results")
            
            # Debug to Discord
            if debug_channel:
                try:
                    if extracted_pages:
                        await debug_channel.send(f"✅ **Web Extraction SUCCESS**: {len(extracted_pages)} pages extracted, {len(failed_sites)} failed, {len(slow_sites)} slow")
                    else:
                        await debug_channel.send(f"❌ **Web Extraction FAILED**: 0 pages extracted, {len(failed_sites)} failed, {len(slow_sites)} slow")
                except: pass
            
            # Return results immediately - let caller handle blacklist updates later
            return extracted_pages, {'failed_sites': failed_sites, 'slow_sites': slow_sites}
    
    async def _extract_single_page(self, session: aiohttp.ClientSession, url: str) -> Optional[Dict[str, str]]:
        """Extract content from a single URL"""
        start_time = asyncio.get_event_loop().time()
        try:
            # Check if this is a Reddit URL and use API instead
            if 'reddit.com' in url:
                result = await self._extract_reddit_content(session, url)
                if result:
                    result['response_time'] = asyncio.get_event_loop().time() - start_time
                return result
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            async with session.get(url, headers=headers) as response:
                if response.status != 200:
                    return None
                
                # Check content type
                content_type = response.headers.get('content-type', '').lower()
                if 'text/html' not in content_type:
                    return None
                
                html_content = await response.text()
                
                # Parse with BeautifulSoup using faster parser if available
                soup = BeautifulSoup(html_content, 'lxml' if 'lxml' in str(BeautifulSoup) else 'html.parser')
                
                # Extract title
                title = soup.find('title')
                title_text = title.get_text().strip() if title else urlparse(url).netloc
                
                # Clean and extract content
                cleaned_content = self._clean_html_content(soup)
                
                if not cleaned_content or len(cleaned_content.strip()) < 100:
                    return None
                
                # Truncate if too long
                if len(cleaned_content) > self.max_content_length:
                    cleaned_content = cleaned_content[:self.max_content_length] + "..."
                
                # Calculate response time
                response_time = asyncio.get_event_loop().time() - start_time
                
                return {
                    'url': url,
                    'title': title_text,
                    'content': cleaned_content,
                    'length': len(cleaned_content),
                    'response_time': response_time
                }
                
        except Exception as e:
            error_msg = f"Error extracting {url}: {e}"
            print(f"DEBUG: {error_msg}")
            
            # Record failure for potential auto-blocking
            from .domain_filter import get_domain_filter
            domain_filter = get_domain_filter()
            await domain_filter.record_failure(url, str(e))
            
            return None
    
    async def _extract_reddit_content(self, session: aiohttp.ClientSession, url: str) -> Optional[Dict[str, str]]:
        """Extract content from Reddit using authenticated API"""
        try:
            from ..config import config
            from .reddit_client import RedditClient
            
            # Check if Reddit API is configured
            if not config.has_reddit_api():
                # Fallback to public JSON endpoint
                return await self._extract_reddit_json_fallback(session, url)
            
            # Use authenticated Reddit client
            reddit_client = RedditClient()
            data = await reddit_client.get_post_data(session, url)
            
            if not data:
                return None
            
            # Extract content from API response
            result = await reddit_client.extract_content_from_data(data)
            
            if result:
                # Truncate if too long
                if len(result['content']) > self.max_content_length:
                    result['content'] = result['content'][:self.max_content_length] + "..."
                    result['length'] = len(result['content'])
                
                return result
            else:
                return None
                
        except Exception as e:
            error_msg = f"Reddit API extraction failed for {url}: {e}"
            print(f"DEBUG: {error_msg}")
            return None
    
    async def _extract_reddit_json_fallback(self, session: aiohttp.ClientSession, url: str) -> Optional[Dict[str, str]]:
        """Fallback method using public Reddit JSON endpoints"""
        try:
            # Try public JSON endpoint
            json_url = url.rstrip('/') + '.json'
            
            headers = {
                'User-Agent': 'J.A.R.V.I.S Discord Bot 1.0 by /u/CarinXO'
            }
            
            async with session.get(json_url, headers=headers) as response:
                if response.status != 200:
                    return None
                
                data = await response.json()
                
                # Use the same extraction logic as the authenticated client
                from .reddit_client import RedditClient
                reddit_client = RedditClient()
                result = await reddit_client.extract_content_from_data(data)
                
                return result
                
        except Exception as e:
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