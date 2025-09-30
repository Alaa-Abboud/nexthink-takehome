#!/usr/bin/env python3
"""
Quick API Test Script
====================

Fast and simple test of the API endpoints.
"""

import requests
import json
from datetime import datetime, timezone

BASE_URL = "http://localhost:8000"

def test_health():
    """Test health endpoint."""
    print("🏥 Testing health...")
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Health: {data['status']}, Events: {data['checks']['storage']['event_count']}")
        return True
    return False

def test_ingest():
    """Test ingest endpoint."""
    print("\n📥 Testing ingest...")
    
    # Sample events matching your NewsItem schema
    test_events = [
        {
            "id": "test_001",
            "source": "reddit_r_sysadmin", 
            "title": "Critical Database Security Vulnerability Found",
            "body": "A severe security flaw affecting production databases has been discovered. Immediate patching required.",
            "published_at": datetime.now(timezone.utc).isoformat(),
            "score": 0.0,
            "url": "https://reddit.com/test_001"
        },
        {
            "id": "test_002",
            "source": "rss_arstechnica_com",
            "title": "AWS Services Experience Global Outage", 
            "body": "Amazon Web Services experiencing widespread downtime affecting enterprise customers worldwide.",
            "published_at": datetime.now(timezone.utc).isoformat(),
            "score": 0.0,
            "url": "https://arstechnica.com/test_002"
        },
        {
            "id": "test_003",
            "source": "reddit_r_cybersecurity",
            "title": "New Gaming Laptop Released",
            "body": "Latest gaming laptop features RGB lighting and can run all modern games at high settings.",
            "published_at": "2025-09-25T12:00:00Z",
            "score": 0.0,
            "url": "https://reddit.com/test_003"
        },
    ]
    
    response = requests.post(
        f"{BASE_URL}/ingest",
        json=test_events,
        headers={"Content-Type": "application/json"}
    )
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Received: {data['received']}, Added: {data['added']}, Status: {data['status']}")
        return data['added'] > 0
    else:
        print(f"Error: {response.text}")
        return False

def test_retrieve():
    """Test retrieve endpoint."""
    print("\n📤 Testing retrieve...")
    
    response = requests.get(f"{BASE_URL}/retrieve")
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        events = response.json()
        print(f"Retrieved {len(events)} events")
        
        if events:
            print("Sample events:")
            for i, event in enumerate(events[:2], 1):
                print(f"  {i}. {event['title'][:50]}... (score: {event.get('score', 'N/A')})")
        return True
    else:
        print(f"Error: {response.text}")
        return False

def test_stats():
    """Test stats endpoint."""
    print("\n📊 Testing stats...")
    
    response = requests.get(f"{BASE_URL}/stats")
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        stats = response.json()
        print(f"Total events: {stats['total_events']}")
        print(f"Average score: {stats['average_relevance_score']}")
        print(f"Sources: {list(stats['sources'].keys())}")
        return True
    else:
        print(f"Error: {response.text}")
        return False

def main():
    """Run quick API tests."""
    print("🚀 Quick API Test")
    print("=" * 30)
    print("Make sure your API is running: python your_api_file.py")
    print()
    
    try:
        # Test in sequence
        results = []
        results.append(test_health())
        results.append(test_ingest()) 
        results.append(test_retrieve())
        results.append(test_stats())
        
        print("\n" + "=" * 30)
        passed = sum(results)
        total = len(results)
        
        if passed == total:
            print(f"✅ All {total} tests passed!")
        else:
            print(f"⚠️  {passed}/{total} tests passed")
            
        print(f"\n📖 API Docs: {BASE_URL}/docs")
        
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to API. Make sure it's running on http://localhost:8000")
    except Exception as e:
        print(f"❌ Test failed: {e}")

if __name__ == "__main__":
    main()