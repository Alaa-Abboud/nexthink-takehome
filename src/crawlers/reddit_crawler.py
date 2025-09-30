import logging
from typing import Any
from datetime import datetime, timezone

import aiohttp

from src.crawlers.schemas import NewsItem
from src.crawlers.base_crawler import BaseCrawler
from src.config import ITEM_LIMIT_PER_SOURCE_PER_POLL

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
        url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit={min(limit, 25)}"
        headers = {'User-Agent': self.user_agent}
        
        try:
            async with session.get(url, headers=headers, timeout=30) as response:
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
                        title=post_data.get('title', ''),
                        body=post_data.get('selftext', ''),
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
