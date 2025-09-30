#!/usr/bin/env python3
"""
Quick Crawlers Check
======================

Ultra-simple script to quickly verify crawlers work.
"""

import asyncio
from datetime import datetime

from src.crawlers.all_crawlers import RedditCrawler, RSSCrawler, MockCrawler

async def quick_reddit_check():
    """Quick Reddit check - just one item."""
    print("🔴 Reddit check...", end=" ", flush=True)
    
    config = {
        'source_name': 'reddit_test',
        'subreddits': ['sysadmin'], 
        'rate_limit': 2.0,
        'user_agent': 'ITNewsAgentTest/1.0'
    }
    
    try:
        crawler = RedditCrawler(config)
        items = await crawler.fetch_items(limit=10)
        
        if items and len(items) > 0:
            item = items[0]
            print(f"✅ Got: '{item.title[:40]}...'")
            return True
        else:
            print("⚠️  No items returned")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


async def quick_rss_check():
    """Quick RSS check - just one item."""
    print("📡 RSS check...", end=" ", flush=True)
    
    config = {
        'rss_urls': ['https://arstechnica.com/feed/'],
        'rate_limit': 1.0
    }
    
    try:
        crawler = RSSCrawler(config)
        items = await crawler.fetch_items(limit=1)
        
        if items and len(items) > 0:
            item = items[0]
            print(f"✅ Got: '{item.title[:40]}...'")
            return True
        else:
            print("⚠️  No items returned")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


async def quick_mock_check():
    """Quick mock check."""
    print("🎭 Mock check...", end=" ", flush=True)
    
    try:
        crawler = MockCrawler({'source_name': 'test'})
        
        # Inject test data
        test_data = [{
            'id': 'test_1',
            'source': 'test',
            'title': 'Test Item',
            'body': 'Test body content',
            'published_at': datetime.now().isoformat()
        }]
        
        crawler.inject_items(test_data)
        items = await crawler.fetch_items()
        
        if items and len(items) > 0:
            print("✅ Works correctly")
            return True
        else:
            print("❌ No items returned")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


async def main():
    """Run all quick checks."""
    print("🚀 Quick Crawlers Check")
    print("-" * 25)
    
    start_time = datetime.now()
    
    # Run checks
    results = []
    results.append(await quick_mock_check())
    results.append(await quick_reddit_check())
    results.append(await quick_rss_check())
    
    elapsed = datetime.now() - start_time
    
    # Summary
    print("-" * 25)
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"🎉 All {total} checks passed! ({elapsed.total_seconds():.1f}s)")
    else:
        print(f"⚠️  {passed}/{total} checks passed ({elapsed.total_seconds():.1f}s)")
        

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Test interrupted by user")
    except Exception as e:
        print(f"💥 Unexpected error: {e}")