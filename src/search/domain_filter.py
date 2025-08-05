"""
Domain filtering system for blocking problematic websites
Maintains a dynamic blacklist of domains that fail extraction
"""

import json
import asyncio
from datetime import datetime
from typing import Dict, List, Set, Optional
from urllib.parse import urlparse
from pathlib import Path
from ..utils.logging import get_logger

logger = get_logger(__name__)


class DomainFilter:
    """Manages blocked domains and filters search results"""
    
    def __init__(self, blocked_domains_file: str = "data/blocked_domains.json"):
        self.blocked_domains_file = Path(blocked_domains_file)
        self.blocked_domains: Dict[str, Dict] = {}
        self.temporary_failures: Dict[str, Dict] = {}
        self.whitelist: Set[str] = set()
        self.config: Dict = {}
        self._lock = asyncio.Lock()
        self._load_blocked_domains()
    
    def _load_blocked_domains(self):
        """Load blocked domains from file"""
        try:
            if self.blocked_domains_file.exists():
                with open(self.blocked_domains_file, 'r') as f:
                    data = json.load(f)
                    self.blocked_domains = data.get('blocked_domains', {})
                    self.temporary_failures = data.get('temporary_failures', {})
                    self.whitelist = set(data.get('whitelist', []))
                    self.config = data.get('config', {
                        'max_failures_before_block': 3,
                        'auto_block_enabled': True,
                        'version': '1.0'
                    })
                logger.info(f"Loaded {len(self.blocked_domains)} blocked domains")
            else:
                logger.info("No blocked domains file found, starting fresh")
                self.config = {
                    'max_failures_before_block': 3,
                    'auto_block_enabled': True,
                    'version': '1.0'
                }
        except Exception as e:
            logger.error(f"Error loading blocked domains: {e}")
            self.blocked_domains = {}
            self.temporary_failures = {}
            self.whitelist = set()
    
    async def _save_blocked_domains(self):
        """Save blocked domains to file"""
        try:
            async with self._lock:
                data = {
                    'blocked_domains': self.blocked_domains,
                    'temporary_failures': self.temporary_failures,
                    'whitelist': list(self.whitelist),
                    'config': self.config
                }
                
                # Ensure directory exists
                self.blocked_domains_file.parent.mkdir(parents=True, exist_ok=True)
                
                with open(self.blocked_domains_file, 'w') as f:
                    json.dump(data, f, indent=2)
                    
        except Exception as e:
            logger.error(f"Error saving blocked domains: {e}")
    
    def extract_domain(self, url: str) -> str:
        """Extract domain from URL"""
        try:
            parsed = urlparse(url)
            return parsed.netloc.lower()
        except:
            return url.lower()
    
    def is_blocked(self, url: str) -> bool:
        """Check if a domain is blocked"""
        domain = self.extract_domain(url)
        
        # Check whitelist first
        if domain in self.whitelist:
            return False
            
        # Check blocked domains
        return domain in self.blocked_domains
    
    def should_skip_domain(self, url: str) -> tuple[bool, str]:
        """Check if domain should be skipped, return (should_skip, reason)"""
        domain = self.extract_domain(url)
        
        # Check whitelist
        if domain in self.whitelist:
            return False, "whitelisted"
        
        # Check blocked domains
        if domain in self.blocked_domains:
            reason = self.blocked_domains[domain].get('reason', 'blocked')
            return True, f"blocked: {reason}"
        
        return False, "allowed"
    
    async def record_failure(self, url: str, error_message: str, debug_channel=None):
        """Record a failure for a domain and potentially block it"""
        domain = self.extract_domain(url)
        
        # Skip if whitelisted
        if domain in self.whitelist:
            return
        
        # Don't auto-block if disabled
        if not self.config.get('auto_block_enabled', True):
            return
        
        # Update failure count
        if domain not in self.temporary_failures:
            self.temporary_failures[domain] = {
                'failure_count': 0,
                'first_failure': datetime.now().isoformat(),
                'last_failure': error_message
            }
        
        self.temporary_failures[domain]['failure_count'] += 1
        self.temporary_failures[domain]['last_failure'] = error_message
        self.temporary_failures[domain]['last_failure_time'] = datetime.now().isoformat()
        
        failure_count = self.temporary_failures[domain]['failure_count']
        max_failures = self.config.get('max_failures_before_block', 3)
        
        # Block domain if it exceeds failure threshold
        if failure_count >= max_failures:
            await self.block_domain(domain, f"Auto-blocked after {failure_count} failures", error_message, debug_channel)
            # Move from temporary to blocked
            del self.temporary_failures[domain]
        else:
            if debug_channel:
                await debug_channel.send(f"🔧 **Debug**: Domain `{domain}` failure {failure_count}/{max_failures}: {error_message}")
        
        await self._save_blocked_domains()
    
    async def block_domain(self, domain: str, reason: str, last_error: str = "", debug_channel=None):
        """Manually block a domain"""
        self.blocked_domains[domain] = {
            'reason': reason,
            'blocked_at': datetime.now().isoformat(),
            'failure_count': self.temporary_failures.get(domain, {}).get('failure_count', 1),
            'last_failure': last_error
        }
        
        if debug_channel:
            await debug_channel.send(f"🚫 **Domain Blocked**: `{domain}` - {reason}")
        
        logger.info(f"Blocked domain: {domain} - {reason}")
        await self._save_blocked_domains()
    
    async def unblock_domain(self, domain: str, debug_channel=None):
        """Remove a domain from the blocklist"""
        if domain in self.blocked_domains:
            del self.blocked_domains[domain]
            await self._save_blocked_domains()
            
            if debug_channel:
                await debug_channel.send(f"✅ **Domain Unblocked**: `{domain}`")
            
            logger.info(f"Unblocked domain: {domain}")
    
    def add_to_whitelist(self, domain: str):
        """Add domain to whitelist (never block)"""
        self.whitelist.add(domain.lower())
        # Remove from blocked if present
        if domain in self.blocked_domains:
            del self.blocked_domains[domain]
        logger.info(f"Added to whitelist: {domain}")
    
    def filter_urls(self, urls: List[str]) -> tuple[List[str], List[str]]:
        """Filter URLs, return (allowed_urls, blocked_urls)"""
        allowed = []
        blocked = []
        
        for url in urls:
            should_skip, reason = self.should_skip_domain(url)
            if should_skip:
                blocked.append((url, reason))
            else:
                allowed.append(url)
        
        return allowed, blocked
    
    def get_stats(self) -> Dict:
        """Get filtering statistics"""
        return {
            'blocked_domains': len(self.blocked_domains),
            'temporary_failures': len(self.temporary_failures),
            'whitelisted_domains': len(self.whitelist),
            'auto_block_enabled': self.config.get('auto_block_enabled', True),
            'max_failures_threshold': self.config.get('max_failures_before_block', 3)
        }
    
    def list_blocked_domains(self) -> List[tuple[str, str]]:
        """Get list of blocked domains with reasons"""
        return [(domain, data.get('reason', 'Unknown')) for domain, data in self.blocked_domains.items()]


# Global domain filter instance
_domain_filter = None

def get_domain_filter() -> DomainFilter:
    """Get or create global domain filter instance"""
    global _domain_filter
    if _domain_filter is None:
        _domain_filter = DomainFilter()
    return _domain_filter