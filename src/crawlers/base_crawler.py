import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any
import time

from src.crawlers.schemas import NewsItem
from src.config import DEFAULT_RATE_LIMIT, ITEM_LIMIT_PER_SOURCE_PER_POLL

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

    
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
