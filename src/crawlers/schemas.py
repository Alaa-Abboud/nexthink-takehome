import hashlib
from typing import Any
from datetime import datetime, timezone

from pydantic import BaseModel, Field, field_validator

# ===== SCHEMA - PYDANTIC =====

class NewsItem(BaseModel):
    """
    Pydantic-based model. Represents a standardized news item from any source.
    """
    
    # Core fields with validation
    id: str = Field(..., description="News item ID")
    source: str = Field(..., description="News item source (e.g. Reddit)")
    title: str = Field(..., description="News item title")
    body: str | None = Field(None, description="News item content (Optional)")
    published_at: datetime = Field(..., description="News item publish date (UTC - ISO)")
    score: float = Field(0.0, description="Ranking score (Relevance x Recency)")
    url: str = Field("", description="Source URL")
    
    @field_validator('published_at', mode='before')
    @classmethod
    def parse_published_at(cls, v) -> datetime:
        """
        Convert string timestamps to datetime objects.
        """
        if isinstance(v, datetime):
            return v
        
        if isinstance(v, str):
            try:
                return datetime.fromisoformat(v.replace('Z', '+00:00')) 
                # if v.endswith('Z') else datetime.fromisoformat(v)
            
            except ValueError:
                raise ValueError(f'Invalid published_at format: {v}')
        
        raise ValueError(f'published_at must be a string or datetime, got: {type(v)}')
    
    def to_dict(self) -> dict[str, Any]:
        """
        Convert to dictionary format for API compliance.
        """
        data = self.model_dump()
        if isinstance(data['published_at'], datetime):
            data['published_at'] = data['published_at'].isoformat() # Ensure published_at is ISO string
        
        return data