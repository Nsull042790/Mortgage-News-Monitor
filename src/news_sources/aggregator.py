"""News aggregator that combines multiple news sources."""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

from .base import NewsSource, NewsItem
from .rss_feeds import RSSFeedSource
from .news_apis import NewsAPISource, GNewsSource
from src.config import MORTGAGE_RSS_FEEDS, Config

logger = logging.getLogger(__name__)


class NewsAggregator:
    """Aggregates news from multiple sources."""

    def __init__(
        self,
        sources: Optional[list[NewsSource]] = None,
        include_apis: bool = True,
    ):
        """
        Initialize the news aggregator.

        Args:
            sources: List of NewsSource objects. If None, uses default sources.
            include_apis: Whether to include NewsAPI and GNews sources.
        """
        if sources is not None:
            self.sources = sources
        else:
            self.sources = self._create_default_sources(include_apis)

        logger.info(f"News aggregator initialized with {len(self.sources)} sources")

    def _create_default_sources(self, include_apis: bool = True) -> list[NewsSource]:
        """Create default sources from config."""
        sources = []

        # Add RSS feed sources
        for feed_config in MORTGAGE_RSS_FEEDS:
            source = RSSFeedSource(
                name=feed_config["name"],
                url=feed_config["url"],
                priority=feed_config.get("priority", "medium"),
            )
            sources.append(source)

        # Add API sources if configured and enabled
        if include_apis:
            if Config.NEWS_API_KEY:
                sources.append(NewsAPISource(priority="high"))
                logger.info("Added NewsAPI source")

            if Config.GNEWS_API_KEY:
                sources.append(GNewsSource(priority="high"))
                logger.info("Added GNews source")

        return sources

    def fetch_all(self, max_workers: int = 5) -> list[NewsItem]:
        """
        Fetch news from all sources in parallel.

        Args:
            max_workers: Maximum number of parallel fetch operations

        Returns:
            List of all fetched NewsItem objects, deduplicated by URL
        """
        all_items = []
        seen_urls = set()

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_source = {
                executor.submit(source.fetch): source for source in self.sources
            }

            for future in as_completed(future_to_source):
                source = future_to_source[future]
                try:
                    items = future.result()
                    for item in items:
                        if item.url not in seen_urls:
                            seen_urls.add(item.url)
                            all_items.append(item)
                except Exception as e:
                    logger.error(f"Error fetching from {source.name}: {e}")

        # Sort by importance score (descending), then by date
        all_items.sort(
            key=lambda x: (
                -x.importance_score,
                -(x.published_at.timestamp() if x.published_at else 0),
            )
        )

        logger.info(f"Fetched {len(all_items)} unique items from {len(self.sources)} sources")
        return all_items

    def fetch_rss_only(self, max_workers: int = 5) -> list[NewsItem]:
        """Fetch news from RSS sources only (to conserve API quotas)."""
        rss_sources = [s for s in self.sources if isinstance(s, RSSFeedSource)]

        all_items = []
        seen_urls = set()

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_source = {
                executor.submit(source.fetch): source for source in rss_sources
            }

            for future in as_completed(future_to_source):
                source = future_to_source[future]
                try:
                    items = future.result()
                    for item in items:
                        if item.url not in seen_urls:
                            seen_urls.add(item.url)
                            all_items.append(item)
                except Exception as e:
                    logger.error(f"Error fetching from {source.name}: {e}")

        all_items.sort(
            key=lambda x: (
                -x.importance_score,
                -(x.published_at.timestamp() if x.published_at else 0),
            )
        )

        logger.info(f"Fetched {len(all_items)} unique items from {len(rss_sources)} RSS sources")
        return all_items

    def add_source(self, source: NewsSource) -> None:
        """Add a new news source."""
        self.sources.append(source)
        logger.info(f"Added news source: {source.name}")

    def remove_source(self, name: str) -> bool:
        """Remove a news source by name."""
        original_count = len(self.sources)
        self.sources = [s for s in self.sources if s.name != name]

        if len(self.sources) < original_count:
            logger.info(f"Removed news source: {name}")
            return True
        return False

    def list_sources(self) -> list[dict]:
        """List all configured news sources."""
        return [
            {
                "name": source.name,
                "priority": source.priority,
                "type": type(source).__name__,
            }
            for source in self.sources
        ]
