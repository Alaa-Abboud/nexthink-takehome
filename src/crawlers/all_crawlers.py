"""
IT Newsfeed System - Source Crawlers
====================================

Modular source crawlers for fetching IT-related news from various sources.
Each crawler inherits the BaseCrawler for consistent handling.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any
import time
from datetime import datetime, timezone
from urllib.parse import urlparse
import hashlib
from pydantic import BaseModel, Field, field_validator

import aiohttp
import feedparser

from src.crawlers.schemas import NewsItem
from src.crawlers.utils import sanitize_to_text
from src.config import DEFAULT_RATE_LIMIT, ITEM_LIMIT_PER_SOURCE_PER_POLL, TIMEOUT

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ===== SCHEMA - PYDANTIC =====

class NewsItem(BaseModel):
    """
    Pydantic-based model. Represents a standardized news item from any source.
    """
    
    # Core fields with validation
    id: str = Field(..., description="News item ID")
    source: str = Field(..., description="News item source (e.g. Reddit)")
    title: str = Field(..., description="News item title")
    body: str | None = Field(None, description="News item content (Optional)")
    published_at: datetime = Field(..., description="News item publish date (UTC - ISO)")
    score: float = Field(0.0, description="Ranking score (Relevance x Recency)")
    url: str = Field("", description="Source URL")
    
    @field_validator('published_at', mode='before')
    @classmethod
    def parse_published_at(cls, v) -> datetime:
        """
        Convert string timestamps to datetime objects.
        """
        if isinstance(v, datetime):
            return v
        
        if isinstance(v, str):
            try:
                return datetime.fromisoformat(v.replace('Z', '+00:00')) 
                # if v.endswith('Z') else datetime.fromisoformat(v)
            
            except ValueError:
                raise ValueError(f'Invalid published_at format: {v}')
        
        raise ValueError(f'published_at must be a string or datetime, got: {type(v)}')
    
    def to_dict(self) -> dict[str, Any]:
        """
        Convert to dictionary format for API compliance.
        """
        data = self.model_dump()
        if isinstance(data['published_at'], datetime):
            data['published_at'] = data['published_at'].isoformat() # Ensure published_at is ISO string
        
        return data 
    
# ===== BASE =====

class BaseCrawler(ABC):
    """
    Abstract base class for all news source crawlers.
    """
    
    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.source_name = config.get('source_name', 'unknown')
        self.rate_limit = config.get('rate_limit', DEFAULT_RATE_LIMIT)  # in seconds - must abide by reddit api rate limits.
        self.last_request_time = 0
        
    @abstractmethod
    async def fetch_items(self, limit: int = ITEM_LIMIT_PER_SOURCE_PER_POLL) -> list[NewsItem]:
        """
        Fetch latest news items from the source.
        """
        pass
    
    async def _rate_limit_check(self):
        """
        Enforce rate limiting between requests.
        """
        elapsed = time.time() - self.last_request_time
        if elapsed < self.rate_limit:
            await asyncio.sleep(self.rate_limit - elapsed)
        self.last_request_time = time.time()

# ===== REDDIT =====

class RedditCrawler(BaseCrawler):
    """
    Crawler for Reddit IT subreddits.
    """
    
    def __init__(self, config: dict[str, Any]):
        super().__init__(config)
        self.subreddits = config.get('subreddits', ['sysadmin', 'cybersecurity'])
        self.user_agent = config.get('user_agent', 'ITNewsAgent/1.0')
        
    async def fetch_items(self, limit: int = ITEM_LIMIT_PER_SOURCE_PER_POLL) -> list[NewsItem]:
        """
        Fetch posts from specified subreddits.
        """
        items = []
        
        async with aiohttp.ClientSession() as session:
            for subreddit in self.subreddits:
                try:
                    await self._rate_limit_check()
                    items.extend(await self._fetch_subreddit(session, subreddit, limit))
                except Exception as e:
                    logger.error(f"Error fetching from r/{subreddit}: {e}")
                    
        return items[:limit]
    
    async def _fetch_subreddit(self, session: aiohttp.ClientSession, subreddit: str, limit: int) -> list[NewsItem]:
        """
        Fetch posts from a specific subreddit.
        """

        # default is 25 in reddit - max is capped at 100 - use pagination if more is needed.
        url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit={min(limit, ITEM_LIMIT_PER_SOURCE_PER_POLL)}"
        headers = {'User-Agent': self.user_agent}
        
        try:
            async with session.get(url, headers=headers, timeout=TIMEOUT) as response:
                if response.status != 200:
                    logger.warning(f"Reddit API returned {response.status} for r/{subreddit}")
                    return []
                    
                data = await response.json()
                posts = data.get('data', {}).get('children', [])
                
                items = []
                for post in posts:
                    post_data = post.get('data', {})
                    
                    # Skip pinned posts and ads
                    if post_data.get('stickied') or post_data.get('promoted'):
                        continue
                    
                    item = NewsItem(
                        id=f"reddit_{post_data.get('id')}", # reddit supplies unique id - prefix with reddit to not clash with other source unique ids
                        source=f"reddit_r_{subreddit}",
                        title=sanitize_to_text(post_data.get('title', '')),
                        body=sanitize_to_text(post_data.get('selftext', '')),
                        published_at=datetime.fromtimestamp(post_data.get('created_utc', 0), timezone.utc).isoformat(), # .strftime('%Y-%m-%dT%H:%M:%SZ'),
                        url=f"https://reddit.com{post_data.get('permalink', '')}",
                        score=post_data.get('score', 0), # expected to be zero - to be supplied by us
                    )

                    items.append(item)
                
                logger.info(f"Fetched {len(items)} items from r/{subreddit}")
                return items
                
        except Exception as e:
            logger.error(f"Error parsing Reddit response for r/{subreddit}: {e}")
            return []

# ===== RSS ARTICLES =====

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
            async with session.get(rss_url, headers=self.headers, timeout=TIMEOUT) as response:
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
                    id=f"{source_name}_{hashlib.md5(title.encode('utf-8')).hexdigest()[:16]}", # TODO: short hash - remove slicing (?)
                    source=source_name,
                    title=sanitize_to_text(title),
                    body=sanitize_to_text(description),
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


# ===== MOCK - IS IT NEEDED ? CAN BE USED AS A UI OPTION ? =====

class MockCrawler(BaseCrawler):
    """
    Crawler/aggregator for mock/synthetic data injection.
    """
    
    def __init__(self, config: dict[str, Any]):
        super().__init__(config)
        self.injected_items = []
        
    async def fetch_items(self, limit: int = ITEM_LIMIT_PER_SOURCE_PER_POLL) -> list[NewsItem]:
        """
        Return injected mock items.
        """
        return self.injected_items[:limit]
    
    def inject_items(self, items_data: list[dict[str, Any]]):
        """
        Inject mock items for testing.
        """
        self.injected_items = []
        
        for item_data in items_data:
            try:
                # Parse timestamp if provided
                published_at = datetime.now(timezone.utc)
                if 'published_at' in item_data:
                    published_at = datetime.fromisoformat(
                        item_data['published_at'].replace('Z', '+00:00')
                    )
                
                item = NewsItem(
                    id=item_data['id'],
                    source=item_data['source'],
                    title=item_data['title'],
                    body=item_data.get('body', ''),
                    published_at=published_at
                )
                self.injected_items.append(item)
                
            except Exception as e:
                logger.error(f"Error processing mock item: {e}")
        
        logger.info(f"Injected {len(self.injected_items)} mock items")

# ===== Orchestrator =====

class SourceCrawlerManager:
    """
    Manages multiple source crawlers/aggregators and coordinates fetching.
    """
    
    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.crawlers = {}
        self._initialize_crawlers()
        
    def _initialize_crawlers(self):
        """
        Initialize configured crawlers.
        """
        crawler_configs = self.config.get('crawlers', {})
        
        # Initialize Reddit crawler
        if 'reddit' in crawler_configs:
            self.crawlers['reddit'] = RedditCrawler(crawler_configs['reddit'])
            
        # Initialize news website crawler
        if 'news_websites' in crawler_configs:
            self.crawlers['news_websites'] = RSSCrawler(crawler_configs['news_websites'])
            
        # Always initialize mock crawler for testing
        # self.crawlers['mock'] = MockCrawler({'source_name': 'mock'})
        
        logger.info(f"Initialized {len(self.crawlers)} crawlers: {list(self.crawlers.keys())}")
    
    async def fetch_all_items(self, limit_per_source: int = ITEM_LIMIT_PER_SOURCE_PER_POLL) -> list[NewsItem]:
        """
        Fetch items from all configured crawlers.
        """
        all_items = []
        
        # Fetch from all crawlers concurrently
        tasks = []
        for name, crawler in self.crawlers.items():
            tasks.append(self._fetch_with_error_handling(name, crawler, limit_per_source))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Combine results
        for result in results:
            if isinstance(result, list):
                all_items.extend(result)
            elif isinstance(result, Exception):
                logger.error(f"Crawler error: {result}")
        
        logger.info(f"Fetched total of {len(all_items)} items from all sources")
        return all_items
    
    async def _fetch_with_error_handling(self, name: str, crawler: BaseCrawler, 
                                       limit: int) -> list[NewsItem]:
        """
        Fetch items with error handling.
        """
        try:
            items = await crawler.fetch_items(limit)
            logger.info(f"Crawler '{name}' fetched {len(items)} items")
            return items
        except Exception as e:
            logger.error(f"Error in crawler '{name}': {e}")
            return []
    
    # def get_mock_crawler(self) -> MockCrawler:
    #     """Get the mock crawler for testing."""
    #     return self.crawlers.get('mock')