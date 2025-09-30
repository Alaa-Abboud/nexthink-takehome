#!/usr/bin/env python3
"""
Simple Storage Test Script
=========================

Quick test of a simplified Storage system.
"""

import tempfile
import os
from datetime import datetime, timezone

from src.crawlers.all_crawlers import NewsItem
from src.db.base_storage import NewsItemStorage

def test_basic_operations():
    """Test basic storage operations."""
    print("🗄️  TESTING BASIC STORAGE OPERATIONS")
    print("=" * 40)
    
    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as tmp:
        db_path = tmp.name
    
    try:
        # Initialize storage
        storage = NewsItemStorage(db_path)
        print(f"✅ Created storage: {os.path.basename(db_path)}")
        
        # Create test events
        test_events = [
            {
                'id': 'test_001',
                'source': 'reddit_r_sysadmin',
                'title': 'Critical Database Server Failure',
                'body': 'Main production database has gone offline affecting all services.',
                'published_at': '2025-09-25T12:00:00Z',
                'url': 'https://reddit.com/test_001'
            },
            {
                'id': 'test_002',
                'source': 'rss_arstechnica_com', 
                'title': 'New Zero-Day Vulnerability Disclosed',
                'body': 'Security researchers have found a critical flaw in popular software.',
                'published_at': '2025-09-25T11:30:00Z',
                'url': 'https://arstechnica.com/test_002'
            },
            {
                'id': 'test_003',
                'source': 'reddit_r_cybersecurity',
                'title': 'Major Breach at Fortune 500 Company',
                'body': 'Customer data compromised in sophisticated attack.',
                'published_at': '2025-09-25T10:15:00Z',
                'url': 'https://reddit.com/test_003'
            }
        ]
        
        # Test adding events
        print("📝 Adding test events...")
        result = storage.add_events(test_events)
        print(f"✅ Result: received={result['received']}, added={result['added']}, duplicates={result['duplicates_by_id']}")
        
        assert result['added'] == 3, f"Expected 3 added, got {result['added']}"
        assert result['duplicates_by_id'] == 0, f"Expected 0 duplicates, got {result['duplicates_by_id']}"
        
        # Test duplicate detection
        print("\n🔄 Testing duplicate detection...")
        duplicate_result = storage.add_events(test_events)  # Same events again
        print(f"✅ Duplicate test: received={duplicate_result['received']}, added={duplicate_result['added']}, duplicates={duplicate_result['duplicates_by_id']}")
        
        assert duplicate_result['added'] == 0, "Should not add any duplicates"
        assert duplicate_result['duplicates_by_id'] == 3, "Should detect 3 duplicates"
        
        # Test retrieval
        print("\n📋 Testing event retrieval...")
        all_events = storage.get_all_events()
        print(f"✅ Retrieved {len(all_events)} events")
        
        assert len(all_events) == 3, f"Expected 3 events, got {len(all_events)}"
        
        # Test sorting (newest first)
        # print(f"✅ Events are sorted by publish time:")
        # for i, event in enumerate(all_events[:3], 1):
        #     print(f"   {i}. {event['published_at']} - {event['title'][:50]}...")
        
        # # Verify sorting
        # timestamps = [event['published_at'] for event in all_events]
        # assert timestamps == sorted(timestamps, reverse=True), "Events should be sorted newest first"
        
        # Test count methods
        print(f"\n📊 Event count: {storage.get_event_count()}")
        print(f"📊 Len method: {len(storage)}")
        
        assert storage.get_event_count() == 3
        assert len(storage) == 3
        
        # Test source filtering
        print(f"\n🎯 Testing source filtering...")
        reddit_events = storage.get_events_by_source('reddit_r_sysadmin')
        print(f"✅ Found {len(reddit_events)} events from reddit_r_sysadmin")
        
        assert len(reddit_events) == 1, "Should find 1 event from reddit_r_sysadmin"
        
        # Test event existence check
        print(f"\n🔍 Testing event existence...")
        exists = storage.event_exists('test_001')
        not_exists = storage.event_exists('nonexistent')
        print(f"✅ test_001 exists: {exists}")
        print(f"✅ nonexistent exists: {not_exists}")
        
        assert exists == True
        assert not_exists == False
        
        # Test clearing
        print(f"\n🗑️  Testing clear operation...")
        cleared_count = storage.clear_all_events()
        print(f"✅ Cleared {cleared_count} events")
        
        assert cleared_count == 3
        assert storage.get_event_count() == 0
        
        storage.close()
        print("✅ All basic tests passed!")
        
    finally:
        # Cleanup
        os.unlink(db_path)


def test_newsitem_integration():
    """Test integration with NewsItem objects (if available)."""
    print("\n📰 TESTING NEWSITEM INTEGRATION")
    print("=" * 40)
    
    with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as tmp:
        db_path = tmp.name
    
    try:
        storage = NewsItemStorage(db_path)
        
        # Create mock NewsItem objects
        news_items = [
            NewsItem(
                id='news_001',
                source='test_source',
                title='Mock News Item 1',
                body='This is a test news item.',
                published_at=datetime.now(timezone.utc),
                url='https://example.com/news_001'
            ),
            NewsItem(
                id='news_002',
                source='test_source',
                title='Mock News Item 2', 
                body='This is another test news item.',
                published_at=datetime.now(timezone.utc),
                url='https://example.com/news_002'
            )
        ]
        
        # Test adding NewsItem objects
        print("📝 Adding NewsItem objects...")
        result = storage.add_news_items(news_items)
        print(f"✅ Added {result['added']} NewsItem objects")
        
        assert result['added'] == 2
        
        # Verify they were stored correctly
        stored_events = storage.get_all_events()
        print(f"✅ Verified {len(stored_events)} events in storage")
        
        # Check first item structure
        first_event = stored_events[0]
        required_fields = ['id', 'source', 'title', 'body', 'published_at', 'url']
        
        print("✅ Checking event structure...")
        for field in required_fields:
            assert field in first_event, f"Missing required field: {field}"
            print(f"   ✓ {field}: {first_event[field]}")
        
        storage.close()
        print("✅ NewsItem integration tests passed!")
        
    finally:
        os.unlink(db_path)


def test_db_exit():
    """Test automatic exits."""
    pass

def main():
    """Run all tests."""
    print("🚀 SIMPLIFIED STORAGE SYSTEM TESTS")
    print("=" * 50)
    
    try:
        test_basic_operations()
        test_newsitem_integration() 
        
        print(f"\n🎉 ALL TESTS PASSED!")
        
    except Exception as e:
        print(f"\n💥 TEST FAILED: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()