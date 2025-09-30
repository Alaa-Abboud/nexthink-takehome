import asyncio
import logging

import requests

from src.crawlers.all_crawlers import NewsItem, SourceCrawlerManager
from src.db.base_storage import NewsItemStorage
from src.config import REDDIT_TEST_CONFIG, RSS_TEST_CONFIG, STORAGE_NAME, POLL_INTERVAL, API_BASE_URL, ITEM_LIMIT_PER_SOURCE_PER_POLL, TIMEOUT

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SimpleNewsScheduler:
    """
    Polling scheduler to fetch news items from the different sources at regular intervals.
    """
    def __init__(self):
        # TODO: Add them in a config.py
        self.storage = NewsItemStorage(STORAGE_NAME)
        self.api_base_url = API_BASE_URL
        self.poll_interval: int = POLL_INTERVAL # seconds

        MANAGER_TEST_CONFIG = {'crawlers': {'reddit': REDDIT_TEST_CONFIG, 'news_websites': RSS_TEST_CONFIG}}
        self.crawler = SourceCrawlerManager(MANAGER_TEST_CONFIG)
        
    async def run_once(self):
        """
        Single polling cycle.
        """
        logger.info("Starting fetch cycle...")
        
        try:
            items: list[NewsItem] = await  self.crawler.fetch_all_items(limit_per_source=ITEM_LIMIT_PER_SOURCE_PER_POLL)
            items_json = [item.to_dict() for item in items]

            # call api instead - contains filtering logic?
            # result = self.storage.add_news_items(items)
            result = requests.post(url=f"{self.api_base_url}/ingest",
                                   json=items_json,
                                   headers={"Content-Type": "application/json"},
                                   timeout=TIMEOUT # not in conflict with polling (?)
                                   )    
            
            logger.info(f"Finished Polling Run - Crawled {result.json()['received']} events - Stored {result.json()['added']} new events")
            
        except Exception as e:
            logger.error(f"Fetch cycle failed: {e}")
    
    async def run_forever(self):
        """
        Poll continuously with intervals.
        """
        while True:
            await self.run_once()
            await asyncio.sleep(self.poll_interval)

if __name__ == "__main__":
    scheduler = SimpleNewsScheduler()
    asyncio.run(scheduler.run_forever())