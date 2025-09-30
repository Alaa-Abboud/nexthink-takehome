ITEM_LIMIT_PER_SOURCE_PER_POLL = 25
DEFAULT_RATE_LIMIT = 30 # in seconds
POLL_INTERVAL = 60  # in seconds
TIMEOUT = 60 # in seconds
STORAGE_NAME = 'filtered_events.json'

API_BASE_URL = "http://localhost:8000"

REDDIT_TEST_CONFIG = {
    'source_name': 'reddit',
    'subreddits': ['sysadmin'],  # Start with just one subreddit
    'rate_limit': DEFAULT_RATE_LIMIT,  # should be respectful to source API limits if any
    'user_agent': 'ITNewsfeedLiveTest/1.0'
}

# TODO: rate limit per rss url
RSS_TEST_CONFIG = {
    'source_name': 'rss',
    'rss_urls': [
        'https://arstechnica.com/feed/', # 'https://www.tomshardware.com/feeds/all' 
    ],
    'rate_limit': DEFAULT_RATE_LIMIT
}

