#!/usr/bin/env python3
"""
Crawlers Test Script
===========================

Simple script to test each crawler against real endpoints to verify:
- Network connectivity works
- Data parsing is correct
- Rate limiting is respected
- Error handling works
"""

import asyncio
import logging
import sys
from datetime import datetime, timezone
from typing import Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

from src.crawlers.all_crawlers import (
        RedditCrawler, RSSCrawler, MockCrawler,
        SourceCrawlerManager, NewsItem
    )



# ===== TEST CONFIGURATIONS =====

REDDIT_TEST_CONFIG = {
    'source_name': 'reddit_test',
    'subreddits': ['sysadmin'],  # Start with just one subreddit
    'rate_limit': 2.0,  # Be respectful to Reddit API
    'user_agent': 'ITNewsAgentTest/1.0'
}

RSS_TEST_CONFIG = {
    'source_name': 'rss_test',
    'rss_urls': [
        'https://arstechnica.com/feed/',  # Known reliable RSS feed
        # 'https://www.tomshardware.com/feeds/all'  # Uncomment to test multiple
    ],
    'rate_limit': 1.0
}

MANAGER_TEST_CONFIG = {
    'crawlers': {
        'reddit': REDDIT_TEST_CONFIG,
        'news_websites': RSS_TEST_CONFIG
    }
}


# ===== VALIDATION FUNCTIONS =====

def validate_news_item(item: NewsItem, source_type: str) -> Dict[str, Any]:
    """
    Validate a NewsItem and return validation results.
    """
    results = {
        'valid': True,
        'errors': [],
        'warnings': [],
        'info': {}
    }
    
    # Required field validation
    if not item.id:
        results['errors'].append("Missing required field: id")
        results['valid'] = False
    
    if not item.source:
        results['errors'].append("Missing required field: source")
        results['valid'] = False
    
    if not item.title:
        results['errors'].append("Missing required field: title")
        results['valid'] = False
    
    # Timestamp validation
    if not item.published_at:
        results['errors'].append("Missing published_at timestamp")
        results['valid'] = False
    elif not isinstance(item.published_at, datetime):
        results['errors'].append("published_at is not a datetime object")
        results['valid'] = False
    elif item.published_at.tzinfo is None:
        results['warnings'].append("published_at lacks timezone info")
    
    # Source-specific validations
    if source_type == 'reddit':
        if not item.id.startswith('reddit_'):
            results['warnings'].append("Reddit item ID doesn't start with 'reddit_'")
        if 'reddit.com' not in item.url:
            results['warnings'].append("Reddit item URL doesn't contain 'reddit.com'")
    
    elif source_type == 'rss':
        if not item.url or not item.url.startswith('http'):
            results['warnings'].append("RSS item missing valid URL")
    
    # Collect item info
    results['info'] = {
        'id': item.id,
        'source': item.source,
        'title_length': len(item.title),
        'body_length': len(item.body),
        'has_url': bool(item.url),
        'published_at': item.published_at
    }
    
    return results


def print_validation_summary(results: dict[str, Any], item_count: int):
    """Print a formatted summary of validation results."""
    print(f"\n📊 VALIDATION SUMMARY ({item_count} items)")
    print("=" * 50)
    
    valid_count = sum(1 for r in results.values() if r['valid'])
    print(f"✅ Valid items: {valid_count}/{item_count}")
    print(f"❌ Invalid items: {item_count - valid_count}/{item_count}")
    
    # Count errors and warnings
    total_errors = sum(len(r['errors']) for r in results.values())
    total_warnings = sum(len(r['warnings']) for r in results.values())
    
    print(f"🚨 Total errors: {total_errors}")
    print(f"⚠️  Total warnings: {total_warnings}")
    
    if total_errors > 0:
        print("\n❌ ERRORS:")
        for idx, result in results.items():
            if result['errors']:
                print(f"  Item {idx}: {', '.join(result['errors'])}")
    
    if total_warnings > 0:
        print("\n⚠️  WARNINGS:")
        for idx, result in results.items():
            if result['warnings']:
                print(f"  Item {idx}: {', '.join(result['warnings'])}")


# ===== TEST FUNCTIONS =====

async def test_reddit_crawler():
    """Test Reddit crawler with live data."""
    print("\n🔴 TESTING REDDIT CRAWLER")
    print("=" * 40)
    
    crawler = RedditCrawler(REDDIT_TEST_CONFIG)
    
    try:
        start_time = datetime.now()
        items = await crawler.fetch_items(limit=5)  # Small limit for testing
        elapsed = datetime.now() - start_time
        
        print(f"📈 Fetched {len(items)} items in {elapsed.total_seconds():.2f}s")
        
        if not items:
            print("⚠️  No items returned - check subreddit or network connectivity")
            return
        
        # Validate items
        validation_results = {}
        for i, item in enumerate(items):
            validation_results[i] = validate_news_item(item, 'reddit')
        
        print_validation_summary(validation_results, len(items))
        
        # Show sample item
        if items:
            sample = items[0]
            print(f"\n📄 SAMPLE ITEM:")
            print(f"  ID: {sample.id}")
            print(f"  Source: {sample.source}")
            print(f"  Title: {sample.title[:60]}...")
            print(f"  Body: {sample.body[:100]}...")
            print(f"  Published: {sample.published_at}")
            print(f"  URL: {sample.url}")
            
            # Test serialization
            try:
                item_dict = sample.to_dict()
                print(f"  ✅ Serialization: Success")
                
                # Validate API compliance
                required_fields = ['id', 'source', 'title', 'body', 'published_at']
                missing_fields = [f for f in required_fields if f not in item_dict]
                if missing_fields:
                    print(f"  ❌ Missing API fields: {missing_fields}")
                else:
                    print(f"  ✅ API compliance: All required fields present")
                    
            except Exception as e:
                print(f"  ❌ Serialization error: {e}")
        
    except Exception as e:
        print(f"❌ Reddit crawler failed: {e}")
        logger.exception("Reddit crawler error details:")


async def test_rss_crawler():
    """Test RSS crawler with live data."""
    print("\n📡 TESTING RSS CRAWLER")
    print("=" * 40)
    
    crawler = RSSCrawler(RSS_TEST_CONFIG)
    
    try:
        start_time = datetime.now()
        items = await crawler.fetch_items(limit=5)
        elapsed = datetime.now() - start_time
        
        print(f"📈 Fetched {len(items)} items in {elapsed.total_seconds():.2f}s")
        
        if not items:
            print("⚠️  No items returned - check RSS URLs or network connectivity")
            return
        
        # Validate items
        validation_results = {}
        for i, item in enumerate(items):
            validation_results[i] = validate_news_item(item, 'rss')
        
        print_validation_summary(validation_results, len(items))
        
        # Show sample item
        if items:
            sample = items[0]
            print(f"\n📄 SAMPLE ITEM:")
            print(f"  ID: {sample.id}")
            print(f"  Source: {sample.source}")
            print(f"  Title: {sample.title[:60]}...")
            print(f"  Body: {sample.body[:100]}..." if sample.body else "  Body: (empty)")
            print(f"  Published: {sample.published_at}")
            print(f"  URL: {sample.url}")
            
    except Exception as e:
        print(f"❌ RSS crawler failed: {e}")
        logger.exception("RSS crawler error details:")


async def test_mock_crawler():
    """Test mock crawler with sample data."""
    print("\n🎭 TESTING MOCK CRAWLER")
    print("=" * 40)
    
    crawler = MockCrawler({'source_name': 'mock_test'})
    
    # Create test data that matches the API contract
    test_data = [
        {
            'id': 'mock_001',
            'source': 'mock_source',
            'title': 'Critical Security Vulnerability in Popular Database',
            'body': 'A severe SQL injection vulnerability has been discovered in a widely-used database system. Immediate patching is recommended.',
            'published_at': datetime.now(timezone.utc).isoformat()
        },
        {
            'id': 'mock_002',
            'source': 'mock_source',
            'title': 'Major Cloud Provider Experiences Global Outage',
            'body': 'Services across multiple regions are affected. The provider is working on a resolution.',
            'published_at': (datetime.now(timezone.utc)).isoformat()
        }
    ]
    
    try:
        crawler.inject_items(test_data)
        items = await crawler.fetch_items()
        
        print(f"📈 Injected and retrieved {len(items)} mock items")
        
        # Validate items
        validation_results = {}
        for i, item in enumerate(items):
            validation_results[i] = validate_news_item(item, 'mock')
        
        print_validation_summary(validation_results, len(items))
        
    except Exception as e:
        print(f"❌ Mock crawler failed: {e}")
        logger.exception("Mock crawler error details:")

async def test_rate_limiting():
    """Test rate limiting functionality."""
    print("\n⏱️  TESTING RATE LIMITING")
    print("=" * 40)
    
    config = REDDIT_TEST_CONFIG.copy()
    config['rate_limit'] = 1.0  # 1 second between requests
    
    crawler = RedditCrawler(config)
    
    try:
        start_time = datetime.now()
        
        # Make two consecutive calls
        await crawler._rate_limit_check()
        await crawler._rate_limit_check()
        
        elapsed = datetime.now() - start_time
        
        expected_min_time = config['rate_limit']
        if elapsed.total_seconds() >= expected_min_time:
            print(f"✅ Rate limiting working: {elapsed.total_seconds():.2f}s >= {expected_min_time}s")
        else:
            print(f"⚠️  Rate limiting may not be working: {elapsed.total_seconds():.2f}s < {expected_min_time}s")
            
    except Exception as e:
        print(f"❌ Rate limiting test failed: {e}")


# ===== MAIN TEST RUNNER =====

async def run_all_tests():
    """Run all live tests."""
    print("🚀 STARTING TESTS")
    print("=" * 50)
    
    start_time = datetime.now()
    
    # Run individual crawler tests
    await test_mock_crawler()
    await test_rate_limiting()
    await test_reddit_crawler()
    await test_rss_crawler()
    
    elapsed = datetime.now() - start_time
    print(f"\n🎉 ALL TESTS COMPLETED in {elapsed.total_seconds():.2f}s")
    print("=" * 50)


def main():
    """Main entry point."""
    
    # Allow running specific tests
    if len(sys.argv) > 1:
        test_name = sys.argv[1].lower()
        
        if test_name == 'reddit':
            asyncio.run(test_reddit_crawler())
        elif test_name == 'rss':
            asyncio.run(test_rss_crawler())
        elif test_name == 'mock':
            asyncio.run(test_mock_crawler())
        elif test_name == 'rate':
            asyncio.run(test_rate_limiting())
        else:
            print(f"Unknown test: {test_name}")
            print("Available tests: reddit, rss, mock, rate")
            sys.exit(1)
    else:
        # Run all tests
        asyncio.run(run_all_tests())


if __name__ == "__main__":
    main()