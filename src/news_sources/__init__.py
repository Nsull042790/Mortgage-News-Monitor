"""News sources module for fetching mortgage news from various sources."""

from .base import NewsItem, NewsSource
from .rss_feeds import RSSFeedSource
from .news_apis import NewsAPISource, GNewsSource
from .aggregator import NewsAggregator

__all__ = [
    "NewsItem",
    "NewsSource",
    "RSSFeedSource",
    "NewsAPISource",
    "GNewsSource",
    "NewsAggregator",
]
