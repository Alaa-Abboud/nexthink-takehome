import logging
from typing import Any
from datetime import datetime, timezone

from src.crawlers.schemas import NewsItem
from src.crawlers.base_crawler import BaseCrawler
from src.config import ITEM_LIMIT_PER_SOURCE_PER_POLL

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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