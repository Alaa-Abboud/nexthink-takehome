"""
FastAPI Application for IT Newsfeed System
==========================================

Implements the exact API contract specified in the requirements:
- POST /ingest - Accept raw events and apply content filtering
- GET /retrieve - Return filtered events sorted by importance × recency
"""

import logging
from typing import List, Any
from datetime import datetime, timezone
import traceback
import random
from functools import lru_cache

from fastapi import FastAPI, HTTPException, status, Depends
# from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

from src.crawlers.all_crawlers import NewsItem
from src.db.base_storage import NewsItemStorage
from src.ml.it_critical_filter import ITCriticalFilter
from src.config import STORAGE_NAME

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

#===== RESPONSE SCHEMA ======

class IngestResponse(BaseModel):
    """Response model for /ingest endpoint."""

    status: int = Field(200, description="HTTP status code")
    received: int = Field(..., description="Number of events received")
    added: int = Field(..., description="Number of new events added to storage (post-filtering)")

#====== APP ======
app = FastAPI(
    title="IT Critical News Feed App",
    description="Real-time IT critical news aggregation system with content filtering and scoring",
    version="1.0.0",
    docs_url="/docs",
)

content_filter = ITCriticalFilter() # load once into memory upon API script launch

# Add CORS middleware for development
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

#====== DUMMY SCORING CLASS - USED FOR QUICK TESTING ======
# class DummyContentFilter:
#     def __init__(self):
#         self.relevance_threshold = 0.5
        
#     def calculate_relevance(self, text: str) -> tuple[bool, float]:
#         """Calculate relevance score for IT management news."""
#         score = random.random()
        
#         score = min(score, 1.0)
#         is_relevant = score >= self.relevance_threshold
#         return is_relevant, score


#====== DEPENDENCY FUNCTIONS ======

def get_storage():
    """Dependency factory for storage."""
    return NewsItemStorage(STORAGE_NAME)

@lru_cache()
def get_storage_with_cache():
    """Single shared storage instance."""
    return NewsItemStorage(STORAGE_NAME)


def get_content_filter():
    """Dependency factory for content filter."""
    return ITCriticalFilter()

#====== ENDPOINTS ======

@app.post("/ingest", response_model=IngestResponse, status_code=status.HTTP_200_OK)
async def ingest_events(events: List[NewsItem], 
                        storage: NewsItemStorage = Depends(get_storage),
                        # content_filter: ITCriticalFilter = Depends(get_content_filter)
                        ) -> IngestResponse:
    """
    Ingest raw events endpoint.
    
    Accepts a JSON array of event objects, applies content filtering,
    and stores relevant events with deduplication.
    
    Args:
        events: List of event objects to ingest
        
    Returns:
        IngestResponse: Acknowledgment with processing statistics
    """
    # TODO: handle single-element input (no list)
    # TODO: handle different status responses / codes

    try:
        
        logger.info(f"Received ingest request with {len(events)} events")
        filtered_events = []
        
        # Apply content filtering to each event (if not duplicated)
        for event in events:
            
            # Skip processing for duplicated IDs
            # TODO: add option for duplicated content
            # TODO: Add option to skip over events that were processed but not added before (i.e. filtered out) - currently not stored in DB
            is_duplicated = storage.event_exists(event_id=event.id)
            if is_duplicated:
                logger.debug(f"Event {event.id} already present")
                continue

            # Calculate ranking / relevance score
            text = event.title + '\n' + event.body if event.body else event.title
            is_critical, relevance_score = content_filter.calculate_relevance(text)
            
            if is_critical:
                event_dict = event.to_dict()
                event_dict['score'] = relevance_score
                filtered_events.append(event_dict)
                logger.debug(f"Event {event.id}: score {relevance_score:.3f} - STORED")
            else:
                logger.debug(f"Event {event.id}: score {relevance_score:.3f} - FILTERED OUT")
        
        # Store filtered events with deduplication
        storage_result = storage.add_events(filtered_events) # sotrage.add_news_item()
        
        response = IngestResponse(
            status=200,
            received=len(events),
            added=storage_result["added"],
        )
        
        logger.info(
            f"Ingest completed: {len(events)} crawled - "
            f"{len(filtered_events)} passed filter and ID deduplication - "
            f"{storage_result['added']} added to storage"
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Error during ingest: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ingest failed: {str(e)}"
        )


@app.get("/retrieve", response_model=list[dict[str, Any]])
def retrieve_events(storage: NewsItemStorage = Depends(get_storage)) -> list[dict[str, Any]]:
    """
    Retrieve filtered events endpoint.
    Returns all stored events sorted according relevance score. This ensures deterministic results for automated testing.
    Returns:
        list[dict[str, Any]]: All filtered events in ranked order
    """
    try:
        logger.info("Received retrieve request")
    
        events = storage.get_all_events()
        # Apply secondary sorting by ID for deterministic results - not needed (?) TODO: remove
        events.sort(key=lambda x: (x.get('score', ''), x.get('published_at', '')), reverse=True)
        logger.info(f"Retrieved {len(events)} events")
        return events
        
    except Exception as e:
        logger.error(f"Error during retrieve: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Retrieve failed: {str(e)}"
        )

@app.get("/health")
async def health_check(storage: NewsItemStorage = Depends(get_storage)):
    health = {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": {}
    }
    
    # Test storage
    try:
        event_count = storage.get_event_count()
        health["checks"]["storage"] = {"status": "ok", "event_count": event_count}
    except Exception as e:
        health["checks"]["storage"] = {"status": "error", "message": str(e)}
        health["status"] = "unhealthy"
    
    if health["status"] == "unhealthy":
        raise HTTPException(status_code=503, detail=health)
    
    # TODO: Add other checks
    
    return health

@app.get("/stats")
async def get_statistics(storage: NewsItemStorage = Depends(get_storage)):
    """
    Get preliminary system statistics.
    """
    try:
        all_events = storage.get_all_events()
        
        # Count by source
        source_counts = {}
        relevance_scores = []
        
        for event in all_events:
            source = event.get('source', 'unknown')
            source_counts[source] = source_counts.get(source, 0) + 1
            
            if 'score' in event:
                relevance_scores.append(event['score'])
        
        avg_relevance = sum(relevance_scores) / len(relevance_scores) if relevance_scores else 0.0
        
        return {
            "total_events": len(all_events),
            "sources": source_counts,
            "average_relevance_score": round(avg_relevance, 3),
            "relevance_distribution": {
                "min": min(relevance_scores) if relevance_scores else 0,
                "max": max(relevance_scores) if relevance_scores else 0,
                "avg": round(avg_relevance, 3)
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Statistics failed: {str(e)}"
        )


@app.delete("/events")
async def clear_events(storage: NewsItemStorage = Depends(get_storage)):
    """
    Clear all events in DB.
    """
    try:
        cleared = storage.clear_all_events()
        return {
            "status": "success", 
            "cleared_events": cleared,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    except Exception as e:
        logger.error(f"Error clearing events: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Clear failed: {str(e)}"
        )


def main():
    """Run the API server."""
    logger.info("Starting IT News Feed API server...")
    
    uvicorn.run(
        "src.routers.endpoints:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Enable auto-reload during development
        log_level="info"
    )

if __name__ == "__main__":
    main()