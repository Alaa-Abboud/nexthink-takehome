import streamlit as st
from datetime import datetime, timedelta, timezone
from typing import Literal
import sys
import os
import math

# Add parent directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from src.db.base_storage import NewsItemStorage
from src.config import STORAGE_NAME, POLL_INTERVAL

class SimpleNewsDashboard:
    def __init__(self):
        self.storage = NewsItemStorage(STORAGE_NAME)
        self.setup_page()
    
    def setup_page(self):
        """Configure Streamlit page settings."""
        st.set_page_config(
            page_title="IT News Feed",
            page_icon="",
            layout="wide"
        )
        
        # Clean CSS styling
        st.markdown("""
        <style>
        .main > div {
            padding-top: 0.5rem;
        }
        .news-item {
            background: #f8f9fa;
            padding: 0.6rem 0.8rem;
            border-radius: 6px;
            margin-bottom: 0.5rem;
            border-left: 3px solid #007bff;
            box-shadow: 0 1px 2px rgba(0,0,0,0.05);
        }
        .score-high { color: #dc3545; font-weight: bold; font-size: 0.85rem; }
        .score-medium { color: #fd7e14; font-weight: bold; font-size: 0.85rem; }
        .score-low { color: #28a745; font-weight: bold; font-size: 0.85rem; }
        .source-tag { 
            background: #e9ecef; 
            padding: 0.15rem 0.4rem; 
            border-radius: 3px; 
            font-size: 0.75rem;
            color: #495057;
        }
        .stSelectbox > div > div {
            height: 2.5rem;
        }
        .stSelectbox > div > div > div {
            font-size: 0.9rem;
        }
        /* Reduce spacing between elements */
        .element-container {
            margin-bottom: 0.5rem;
        }
        .stMarkdown {
            margin-bottom: 0.5rem;
        }
        </style>
        """, unsafe_allow_html=True)

    def run(self):
        """Main dashboard entry point."""
        # Compact header
        col1, col2 = st.columns([2, 1])
        with col1:
            st.markdown("## IT News Feed")
            st.markdown("*Latest filtered IT news ranked by **criticality** and recency*")
        
        # Load news data
        events = self.load_events()
        
        if not events:
            st.info("🔄 No news items available. System may be collecting data...")
            return
        
        # Display summary metrics - more compact
        self.display_summary(events)
        
        # Display news feed
        self.display_news_feed(events)

    def display_summary(self, events: list[dict]):
        """Display quick summary statistics."""
        total = len(events)
        high_relevance = len([e for e in events if e.get('score', 0) >= 0.85])
        sources = set(self.format_source_name(e.get('source', 'unknown')) for e in events)
        recent_24h = len([e for e in events if self.is_recent(e, hours=24)])
        
        # Compact metrics in a single line
        st.markdown(f"""
        <div style="background: #f8f9fa; padding: 0.8rem; border-radius: 8px; margin: 0.3rem 0 0.8rem 0; border: 1px solid #e9ecef; text-align: center;">
        <strong>{total}</strong> articles &nbsp;&nbsp;|&nbsp;&nbsp; <strong>🔥 {high_relevance}</strong> high relevance &nbsp;&nbsp;|&nbsp;&nbsp; <strong>{len(sources)}</strong> sources present &nbsp;&nbsp;|&nbsp;&nbsp; <strong>{recent_24h}</strong> items in last 24h
        </div>
        """, unsafe_allow_html=True)

    def display_news_feed(self, events: list[dict]):
        """Display the main news feed."""
        # Main content and config columns
        col1, col2 = st.columns([3, 1])
        
        with col1:
            # System configuration display
            st.markdown("""
            <div style="font-size: 0.7rem; color: #666; margin-bottom: 0.5rem;">
            ⚙️ <strong>Config:</strong> Poll: {} sec | Updated: {}
            </div>
            """.format(POLL_INTERVAL, datetime.now().strftime("%H:%M:%S")), unsafe_allow_html=True)
            
            # Control row with compact dropdowns
            control_col1, control_col2, control_col3 = st.columns([1, 1, 2])
            
            with control_col1:
                sort_by = st.selectbox(
                    "Sort:",
                    ["Relevance", "Recency", "Relevance x Recency"],
                    index=0,
                    key="sort_select"
                )
            
            with control_col2:
                limit = st.selectbox(
                    "Show:",
                    [10, 25, 50, 100],
                    index=1,  # Default to 25
                    key="limit_select",
                    format_func=lambda x: f"{x} items"
                )
        
        with col2:
            pass
        
        # Sort events
        sorted_events = self.sort_events(events, sort_by)
        
        # Simplified sidebar - no filters
        with st.sidebar:
            st.markdown('<hr style="margin: 1rem 0; border: none; border-top: 1px solid #ddd;">', unsafe_allow_html=True)
            
            st.markdown("""
            <div style="font-size: 0.7rem; color: #999; line-height: 1.3;">
            <strong>About:</strong> IT news from Reddit r/sysadmin, Tom's Hardware, and Ars Technica. Articles filtered and scored by IT operations relevance.
            </div>
            """, unsafe_allow_html=True)
        
        # Apply limit (no filters)
        limited_events = sorted_events[:limit]
        
        st.subheader(f"📋 News ({len(limited_events)} of {len(sorted_events)} total)")
        
        # Display articles
        for i, article in enumerate(limited_events):
            self.display_article(article, sort_by)

    def display_article(self, article: dict, sort_by: Literal['Relevance', 'Relevance x Recency']):
        """Display a single news article."""
        score = article.get('score', 0) if sort_by == 'Relevance' else article.get("_hybrid_score", article.get('score', 0))
        title = article.get('title', 'Untitled')
        content = article.get('body') or 'No content available'
        content_truncated = content[:300]
        source = self.format_source_name(article.get('source', 'unknown'))
        timestamp = article.get('published_at', '')
        url = article.get('url', '') or article.get('link', '')
        
        # Score styling
        if score >= 0.85:
            score_class = "score-high"
            score_icon = "🔥"
        elif score >= 0.65:
            score_class = "score-medium"  
            score_icon = "⚡"
        else:
            score_class = "score-low"
            score_icon = "💡"
        
        # Make title clickable if URL exists
        if url:
            title_html = f'<a href="{url}" target="_blank" style="text-decoration: none; color: #333;">{score_icon} {title}</a>'
        else:
            title_html = f"{score_icon} {title}"
        
        # Article container
        with st.container():
            st.markdown(f"""
            <div class="news-item">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.4rem;">
                    <h5 style="margin: 0; font-size: 1rem; line-height: 1.3;">{title_html}</h5>
                    <span class="{score_class}">{score:.3f}</span>
                </div>
                <div style="margin-bottom: 0.4rem;">
                    <span class="source-tag">{source}</span>
                    <span style="color: #6c757d; margin-left: 0.8rem; font-size: 0.8rem;">
                        {self.format_timestamp(timestamp)}
                    </span>
                    {f'<a href="{url}" target="_blank" style="margin-left: 0.8rem; font-size: 0.8rem; color: #007bff; text-decoration: none;">🔗 Read</a>' if url else '<a></a>'}
                </div>
                <p style="margin: 0; color: #555; line-height: 1.3; font-size: 0.9rem;">
                    {content_truncated}{'...' if len(content) > 300 else ''}
                </p>
            </div>
            """, unsafe_allow_html=True)

    def sort_events(self, events: list[dict], sort_by: str) -> list[dict]:
        """Sort events based on selected criteria."""
        if sort_by == "Relevance":
            return sorted(events, key=lambda x: x.get('score', 0), reverse=True)
        
        elif sort_by == "Recency":
            # return sorted(events, key=lambda x: x.get('published_at', ''), reverse=True)
            def parse_date(e):
                ts = e.get('published_at')
                if not ts:
                    return datetime.min.replace(tzinfo=timezone.utc)  # fallback
                try:
                    dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    return dt
                except Exception:
                    return datetime.min.replace(tzinfo=timezone.utc)
            return sorted(events, key=parse_date, reverse=True)
        
        elif sort_by == "Relevance x Recency":
            half_life = 24.0  # hours until score halves
            now = datetime.now(timezone.utc)

            def compute_hybrid(e):
                score = e.get('score', 0.0)
                ts = e.get('published_at')
                if not ts:
                    return 0.0
                try:
                    dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    age_hours = (now - dt).total_seconds() / 3600
                    decay = math.exp(-age_hours / half_life)
                    return score * decay
                except Exception:
                    return score * 0.1  # penalize if timestamp broken

            # annotate each event with its hybrid score
            for e in events:
                e["_hybrid_score"] = compute_hybrid(e)
            return sorted(events, key=lambda e: e["_hybrid_score"], reverse=True)
        else:
            return events

    def load_events(self) -> list[dict]:
        """Load events from storage."""
        try:
            return self.storage.get_all_events()
        except Exception as e:
            st.error(f"Error loading news data: {str(e)}")
            return []

    def format_source_name(self, source: str) -> str:
        """Format source name for display."""
        if 'reddit' in source.lower():
            return "Reddit"
        elif 'tomshardware' in source.lower():
            return "Tom's Hardware"
        elif 'arstechnica' in source.lower():
            return "Ars Technica"
        else:
            return source.replace('_', ' ').title()

    def is_recent(self, event: dict, hours: int = 24) -> bool:
        """Check if event is within the last N hours."""
        timestamp = event.get('published_at', '')
        if not timestamp:
            return False
        
        try:
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            now = datetime.now(dt.tzinfo)
            return now - dt < timedelta(hours=hours)
        except Exception:
            return False

    def format_timestamp(self, timestamp: str) -> str:
        """Format timestamp for display."""
        if not timestamp:
            return "Unknown time"
        
        try:
            # Parse and normalize to UTC
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)

            now = datetime.now(timezone.utc)
            diff = now - dt
            seconds = int(diff.total_seconds())

            if seconds < 0:  # future timestamp
                return "just now"

            days = seconds // 86400
            if days > 0:
                return f"{days} day{'s' if days > 1 else ''} ago"
            hours = seconds // 3600
            if hours > 0:
                return f"{hours} hour{'s' if hours > 1 else ''} ago"
            minutes = max(1, seconds // 60)
            return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
        except Exception:
            return timestamp
            
def main():
    """Main application entry point."""
    dashboard = SimpleNewsDashboard()
    dashboard.run()


if __name__ == "__main__":
    main()