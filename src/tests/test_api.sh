#!/bin/bash
# API Test Cases for IT News Feed System
# Run these commands to test the /ingest and /retrieve endpoints

echo "=== IT News Feed API Test Cases ==="
echo "Make sure the API server is running on localhost:8000"
echo ""

# Base URL
BASE_URL="http://localhost:8000"

echo "1. Health Check"
echo "==============="
curl -X GET "$BASE_URL/health" | jq
echo -e "\n"

echo "2. Test /ingest with IT-relevant events (should pass filter)"
echo "==========================================================="
curl -X POST "$BASE_URL/ingest" \
  -H "Content-Type: application/json" \
  -d '[
    {
      "id": "sec-001",
      "source": "reddit",
      "title": "Critical security vulnerability discovered in Apache Log4j",
      "body": "A severe remote code execution vulnerability has been found in Apache Log4j library affecting millions of applications worldwide. Immediate patching required.",
      "published_at": "2025-09-30T10:30:00Z"
    },
    {
      "id": "outage-001", 
      "source": "ars-technica",
      "title": "AWS experiencing widespread outage affecting multiple services",
      "body": "Amazon Web Services is currently experiencing a major outage impacting EC2, S3, and RDS services across multiple regions. Service restoration in progress.",
      "published_at": "2025-09-30T09:45:00Z"
    },
    {
      "id": "bug-001",
      "source": "tom-hardware",
      "title": "Microsoft releases emergency patch for critical Windows bug",
      "body": "Microsoft has issued an out-of-band security update to fix a zero-day vulnerability being actively exploited in the wild.",
      "published_at": "2025-09-30T08:15:00Z"
    }
  ]' | jq
echo -e "\n"

echo "3. Test /ingest with non-IT events (should be filtered out)"
echo "========================================================="
curl -X POST "$BASE_URL/ingest" \
  -H "Content-Type: application/json" \
  -d '[
    {
      "id": "sports-001",
      "source": "reddit",
      "title": "Local football team wins championship",
      "body": "The home team defeated their rivals 3-1 in yesterdays final match.",
      "published_at": "2025-09-30T12:00:00Z"
    },
    {
      "id": "weather-001",
      "source": "news-site", 
      "title": "Sunny weather expected this weekend",
      "body": "Meteorologists predict clear skies and warm temperatures for the upcoming weekend.",
      "published_at": "2025-09-30T11:30:00Z"
    }
  ]' | jq
echo -e "\n"

echo "4. Test /ingest with mixed relevant/irrelevant events"
echo "===================================================="
curl -X POST "$BASE_URL/ingest" \
  -H "Content-Type: application/json" \
  -d '[
    {
      "id": "mixed-001",
      "source": "reddit",
      "title": "New database performance optimization techniques",
      "body": "Database administrators are implementing new indexing strategies to improve query performance and reduce server load.",
      "published_at": "2025-09-30T14:20:00Z"
    },
    {
      "id": "mixed-002",
      "source": "tech-blog",
      "title": "Celebrity gossip and entertainment news",
      "body": "Latest updates from Hollywood and celebrity lifestyle trends.",
      "published_at": "2025-09-30T13:45:00Z"
    },
    {
      "id": "mixed-003",
      "source": "security-site",
      "title": "Ransomware attack hits major healthcare provider",
      "body": "A sophisticated ransomware attack has encrypted critical systems at a large hospital network, affecting patient care systems.",
      "published_at": "2025-09-30T15:10:00Z"
    }
  ]' | jq
echo -e "\n"

echo "5. Test /retrieve to get filtered events"
echo "======================================="
curl -X GET "$BASE_URL/retrieve" | jq
echo -e "\n"

echo "6. Test duplicate event ingestion (deduplication)"
echo "================================================"
curl -X POST "$BASE_URL/ingest" \
  -H "Content-Type: application/json" \
  -d '[
    {
      "id": "sec-001",
      "source": "reddit",
      "title": "Critical security vulnerability discovered in Apache Log4j",
      "body": "A severe remote code execution vulnerability has been found in Apache Log4j library affecting millions of applications worldwide. Immediate patching required.",
      "published_at": "2025-09-30T10:30:00Z"
    },
    {
      "id": "new-001",
      "source": "tech-news",
      "title": "Cloud infrastructure maintenance scheduled",
      "body": "Planned maintenance window for cloud infrastructure updates will cause brief service interruption tonight.",
      "published_at": "2025-09-30T16:00:00Z"
    }
  ]' | jq
echo -e "\n"

echo "7. Test /retrieve again to verify deduplication and ordering"
echo "==========================================================="
curl -X GET "$BASE_URL/retrieve" | jq
echo -e "\n"

echo "8. Test invalid timestamp format (should fail validation)"
echo "========================================================"
curl -X POST "$BASE_URL/ingest" \
  -H "Content-Type: application/json" \
  -d '[
    {
      "id": "invalid-001",
      "source": "test",
      "title": "Test event with invalid timestamp",
      "body": "This should fail validation due to invalid timestamp format.",
      "published_at": "not-a-valid-timestamp"
    }
  ]'
echo -e "\n"

echo "9. Test missing required fields (should fail validation)"
echo "======================================================"
curl -X POST "$BASE_URL/ingest" \
  -H "Content-Type: application/json" \
  -d '[
    {
      "source": "test",
      "title": "Test event missing ID field",
      "published_at": "2025-09-30T17:00:00Z"
    }
  ]'
echo -e "\n"

echo "10. Test edge case: empty body field (should work)"
echo "================================================="
curl -X POST "$BASE_URL/ingest" \
  -H "Content-Type: application/json" \
  -d '[
    {
      "id": "edge-001",
      "source": "reddit",
      "title": "Network security alert - immediate action required",
      "body": null,
      "published_at": "2025-09-30T18:00:00"
    }
  ]' | jq
echo -e "\n"

echo "11. Final /retrieve to see all stored events"
echo "==========================================="
curl -X GET "$BASE_URL/retrieve" | jq
echo -e "\n"

echo "12. Check final health status"
echo "============================="
curl -X GET "$BASE_URL/health" | jq
echo -e "\n"

echo "=== Test Cases Complete ==="
echo ""
echo "Expected Results:"
echo "- IT-relevant events (security, outage, bugs, infrastructure) should be stored"
echo "- Non-IT events (sports, weather, celebrity) should be filtered out"
echo "- Events should be sorted by published_at descending (newest first)"
echo "- Duplicate IDs should be deduplicated"
echo "- Invalid timestamps and missing fields should return 422 validation errors"
echo "- Health endpoint should show increasing event counts"