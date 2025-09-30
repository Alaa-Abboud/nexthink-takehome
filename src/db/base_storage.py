"""
Storage System
============================

Persistent storage layer using TinyDB with helper utilities.
"""

import logging
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Any, Optional
from pathlib import Path

from tinydb import TinyDB, Query
from tinydb.storages import JSONStorage
from tinydb.middlewares import CachingMiddleware

from src.crawlers.all_crawlers import NewsItem

logger = logging.getLogger(__name__)


class NewsItemStorage:
    """
    Basic Persistent storage using TinyDB.
    Features:
    - Deduplication by ID and content hash
    - Integration with NewsItem objects
    - utilities
    """

    # TODO: Syncing cache and persistent storage is still faulty - skip caching for now
    # TODO: Updating metadata is still not implemented -> Implement
    # TODO: Change name to BaseStorage
    
    def __init__(self, db_path: str = "persistent_storage.json", enable_caching: bool = False):
        """
        Initialize TinyDB connection with optional caching.
        
        Args:
            db_path: Path to the database file
            enable_caching: Enable TinyDB caching.
        """

        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Configure storage
        storage = CachingMiddleware(JSONStorage) if enable_caching else JSONStorage
        self.db = TinyDB(str(self.db_path), storage=storage, encoding="utf-8", ensure_ascii=False, indent=2)
        
        self.events_table = self.db.table('events')
        # self.metadata_table = self.db.table('metadata')
        self.events = self.db.table('events') # reference to the table - not a copy
        
        # Initialize metadata tracking
        # self._init_metadata()
        logger.info(f"Initialized NewsItemStorage: {self.db_path} (caching: {enable_caching})")
    
    # def _init_metadata(self):
    #     """
    #     Initialize metadata tracking for storage statistics.
    #     """
    #     if not self.metadata_table.all():
    #         self.metadata_table.insert({
    #             'created_at': datetime.now(timezone.utc).isoformat(),
    #             'total_ingested': 0,
    #             'total_filtered': 0,
    #             'last_cleanup': None,
    #             'sources': {}
    #         })
    
    def add_news_items(self, items: list[NewsItem]) -> dict[str, int]:
        """
        Add NewsItem objects to storage. 
        Returns:
            Dictionary with operation statistics
        """

        # Convert NewsItem objects to dictionaries
        events = []
        for item in items:
            if hasattr(item, 'to_dict'):
                event_dict = item.to_dict()
            else:
                continue
            
            # Add content hash for advanced deduplication
            content_hash = self._compute_content_hash(event_dict)
            event_dict['_content_hash'] = content_hash
            event_dict['_ingested_at'] = datetime.now(timezone.utc).isoformat()
            events.append(event_dict)
        
        return self.add_events(events)
    
    def add_events(self, events: list[dict[str, Any]]) -> dict[str, int]:
        """
        Add multiple events with enhanced deduplication.  
        Returns:
            Dictionary with detailed operation statistics
        """
        received_count = len(events)
        added_count = 0
        duplicate_by_id = 0
        duplicate_by_content = 0
        
        Event = Query()
        
        for event in events:
            event_id = event.get('id')
            content_hash = event.get('_content_hash') or self._compute_content_hash(event)
            event['_content_hash'] = content_hash
            
            # Check for ID-based duplicates and content-based duplicates
            existing_by_id = self.events_table.search(Event.id == event_id)
            existing_by_content = self.events_table.search(Event._content_hash == content_hash)
            
            if existing_by_id:
                duplicate_by_id += 1
                logger.debug(f"Skipped ID duplicate: {event_id}")
                
            elif existing_by_content:
                duplicate_by_content += 1
                logger.debug(f"Skipped content duplicate: {event_id}")
                
            else:
                self.events_table.insert(event)
                added_count += 1
                logger.debug(f"Added new event: {event_id}")
                
                # Update source statistics - updates metadata
                # self._update_source_stats(event.get('source', 'unknown'))
        
        # Update metadata
        # self._update_ingestion_stats(received_count)
        
        result = {
            "received": received_count,
            "added": added_count,
            "duplicates_by_id": duplicate_by_id,
            "duplicates_by_content": duplicate_by_content
        }
        
        logger.info(f"Storage operation: {result}")
        return result
    
    def get_all_events(self, 
                      sort_by: str = 'published_at',
                      descending: bool = True,
                      limit: Optional[int] = None,
                      source_filter: Optional[str] = None) -> list[dict[str, Any]]:
        """
        Retrieve events with advanced filtering and sorting.
        
        Args:
            sort_by: Field to sort by ('published_at', '_ingested_at')
            descending: Sort in descending order
            limit: Maximum number of events to return
            source_filter: Filter by source (e.g., 'reddit', 'rss_arstechnica_com')
            
        Returns:
            List of filtered and sorted events
        """
        Event = Query()
        
        # Apply source filter if specified
        if source_filter:
            if source_filter.startswith('reddit'):
                events = self.events_table.search(Event.source.matches(r'reddit.*'))
            elif source_filter.startswith('rss'):
                events = self.events_table.search(Event.source.matches(r'rss.*'))
            else:
                events = self.events_table.search(Event.source == source_filter)
        else:
            events = self.events_table.all()
        
        # Sort events
        if events and sort_by in ['published_at', '_ingested_at']:
            events.sort(key=lambda x: (x.get(sort_by, ''), x.get('id', '')), reverse=descending)
        
        # Apply limit - helpful pagination effect in UI (?)
        if limit and limit > 0:
            events = events[:limit]
        
        logger.info(f"Retrieved {len(events)} events (filter: {source_filter}, limit: {limit})")
        return events
    
    def clear_all_events(self) -> int:
        """
        Clear all events from storage. Returns number of deleted events.
        """
        count = len(self.events_table)
        self.events_table.truncate()
        
        # Reset metadata
        # self.metadata_table.truncate()
        # self._init_metadata()
        
        logger.info(f"Cleared {count} events from storage")
        return count

    def get_events_by_source(self, source: str) -> list[dict[str, Any]]:
        """
        Get events from a specific source name.
        """
        Event = Query()
        events = self.events.search(Event.source == source)
        logger.debug(f"Found {len(events)} events from source: {source}")
        return events
    
    def event_exists(self, event_id: str) -> bool:
        """
        Check if an event with given ID already exists.
        """
        Event = Query()
        return len(self.events.search(Event.id == event_id)) > 0
    
    def close(self):
        """
        Close the database connection.
        """
        self.db.close()
        logger.info("Closed database")

    def get_event_count(self) -> int:
        """
        Get total number of stored items.
        """
        return len(self.events_table)

    def _compute_content_hash(self, event: dict[str, Any]) -> str:
        """
        Compute hash of event content for deduplication.
        """
        # Use title + body for content-based deduplication
        content = f"{event.get('title', '')}{event.get('body', '')}"
        return hashlib.md5(content.encode('utf-8')).hexdigest()[:16]  # Short hash
    
    def _update_source_stats(self, source: str):
        """Update source statistics in metadata."""
        pass
    
    def _update_ingestion_stats(self, ingested: int):
        """Update ingestion statistics."""
        pass

    def _update_filtering_stats(self, filtered: int):
        """Update filtering statistics."""
        pass

    def __len__(self) -> int:
        """Return number of stored events."""
        return len(self.events)

    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
    
# ===== STORAGE FACTORY =====

class StorageManager:
    """
    Factory and manager for different storage instances.
    Having both is helpful for debugging, tracking, and A/B testing.
    """
    
    def __init__(self, base_dir: str = "data"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(exist_ok=True)
        
        self._raw_storage = None
        self._filtered_storage = None
    
    @property
    def raw_storage(self) -> NewsItemStorage:
        """Get or create raw events storage."""
        if self._raw_storage is None:
            self._raw_storage = NewsItemStorage(str(self.base_dir / "events_raw.json"))
        return self._raw_storage
    
    @property  
    def filtered_storage(self) -> NewsItemStorage:
        """Get or create filtered events storage."""
        if self._filtered_storage is None:
            self._filtered_storage = NewsItemStorage(str(self.base_dir / "events_filtered.json"))
        return self._filtered_storage
    
    def get_combined_stats(self) -> dict[str, Any]:
        """Get statistics from both storage instances."""
        return {
            'raw_events': self.raw_storage.get_event_count(),
            'filtered_events': self.filtered_storage.get_event_count()
        }
    
    def clear_all(self) -> dict[str, int]:
        """Cleanup old events from both storages."""
        return {
            'raw_cleaned': self.raw_storage.clear_all_events(),
            'filtered_cleaned': self.filtered_storage.clear_all_events()
        }
    
    def close_all(self):
        """Close all storage connections."""
        if self._raw_storage:
            self._raw_storage.close()
        if self._filtered_storage:
            self._filtered_storage.close()


# ===== CONVENIENCE FUNCTIONS =====

def create_storage(db_path: str = "events.json") -> NewsItemStorage:
    """Create a new NewsItemStorage instance."""
    return NewsItemStorage(db_path)


def create_filtered_storage() -> NewsItemStorage:
    """Create storage for filtered events."""
    return NewsItemStorage("events_filtered.json")


def create_raw_storage() -> NewsItemStorage:
    """Create storage for raw events (if you need to store unfiltered data)."""
    return NewsItemStorage("events_raw.json")