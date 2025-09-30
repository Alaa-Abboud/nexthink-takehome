import logging
from typing import Any
from datetime import datetime, timezone
import hashlib
from urllib.parse import urlparse
import asyncio

import aiohttp
import feedparser

from src.crawlers.schemas import NewsItem
from src.crawlers.base_crawler import BaseCrawler
from src.config import ITEM_LIMIT_PER_SOURCE_PER_POLL

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RSSCrawler(BaseCrawler):
    """
    Crawler for IT news websites (RSS-based).
    """
    
    def __init__(self, config: dict[str, Any]):
        super().__init__(config)

        self.rss_urls = config.get('rss_urls', [])
        self.headers = {'User-Agent': config.get('user_agent', 'ITNewsAgent/1.0'),
                        'Accept': 'application/rss+xml, application/xml, text/xml'}

    async def fetch_items(self, limit: int = ITEM_LIMIT_PER_SOURCE_PER_POLL) -> list[NewsItem]:
        """
        Fetch articles from RSS feeds.
        """
        items = []
        
        async with aiohttp.ClientSession() as session:
            for rss_url in self.rss_urls:
                try:
                    await self._rate_limit_check()
                    items.extend(await self._fetch_rss_feed(session, rss_url))
                except Exception as e:
                    logger.error(f"Error fetching RSS from {rss_url}: {e}")
                    
        return items[:limit]
    
    async def _fetch_rss_feed(self, session: aiohttp.ClientSession, rss_url: str) -> list[NewsItem]:
        """
        Parse RSS feed and extract news items.
        """
        try:
            async with session.get(rss_url, headers=self.headers, timeout=30) as response:
                if response.status != 200:
                    logger.warning(f"RSS feed returned {response.status}: {rss_url}")
                    return []
                
                # Use feedparser instead of regex
                content = await response.read()
                items = await self._parse_with_feedparser(content, rss_url)
                
                logger.info(f"Fetched {len(items)} items from {rss_url}")
                return items
                
        except Exception as e:
            logger.error(f"Error parsing RSS feed {rss_url}: {e}")
            return []
    
    async def _parse_with_feedparser(self, content: bytes, feed_url: str) -> list[NewsItem]:
        """
        Parse RSS using feedparser library.
        """
        items = []
        
        # Extract feed source name from URL
        domain = urlparse(feed_url).netloc
        source_name = f"rss_{domain.replace('.', '_')}"
        
        # Parse with feedparser in thread pool (non-blocking)
        loop = asyncio.get_event_loop()
        feed = await loop.run_in_executor(None, feedparser.parse, content)
        
        if feed.bozo:
            logger.warning(f"RSS parsing issues for {feed_url}: {feed.bozo_exception}")
        
        for entry in feed.entries:
            try:
                # Extract title
                title = getattr(entry, 'title', '').strip()
                if not title:
                    continue
                
                # Extract description/content, link, and date
                description = self._extract_content(entry)
                link = getattr(entry, 'link', '').strip()
                pub_date = self._parse_date(entry)
                
                item = NewsItem(
                    id=f"{source_name}_{hashlib.md5(title.encode()).hexdigest()[:16]}", # short hash
                    source=source_name,
                    title=title,
                    body=description,
                    published_at=pub_date,
                    url=link
                )
                items.append(item)
                
            except Exception as e:
                logger.warning(f"Error parsing RSS item: {e}")
                continue
        
        return items

    def _extract_content(self, entry) -> str:
        """
        Extract body content from RSS entry.
        """

        # Try different content fields
        content_fields = ['content', 'summary', 'description']
        
        for field in content_fields:
            if hasattr(entry, field):
                content = getattr(entry, field)
                if isinstance(content, list) and content:
                    return content[0].get('value', '')
                elif isinstance(content, str) and content.strip():
                    return content.strip()
        return ""
    
    def _parse_date(self, entry) -> str:
        """
        Extract and parse published date to ISO-8601 UTC format.
        """
        
        date_keys = ['published_parsed', 'updated_parsed'] # based on feedparser
        
        for key in date_keys:
            if hasattr(entry, key) and getattr(entry, key):
                try:
                    time_struct = getattr(entry, key)
                    date = datetime(*time_struct[:6])
                    
                    # Ensure UTC timezone
                    if date.tzinfo is None: 
                        date = date.replace(tzinfo=timezone.utc)
                    else:
                        date = date.astimezone(timezone.utc).isoformat()
                    
                    return date # Return ISO-8601/RFC 3339 format - strftime('%Y-%m-%dT%H:%M:%SZ')
                
                except (ValueError, TypeError):
                    continue
        
        # Fallback to current time in UTC
        return datetime.now(timezone.utc).isoformat()