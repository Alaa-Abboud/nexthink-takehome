import logging
from typing import Any
import asyncio


from src.crawlers.schemas import NewsItem
from src.crawlers.base_crawler import BaseCrawler
from src.crawlers.reddit_crawler import RedditCrawler
from src.crawlers.rss_crawler import RSSCrawler
from src.crawlers.mock_crawler import MockCrawler
from src.config import ITEM_LIMIT_PER_SOURCE_PER_POLL

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
    
    async def _fetch_with_error_handling(self, name: str, crawler: BaseCrawler, limit: int) -> list[NewsItem]:
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