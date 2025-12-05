"""News API sources for fetching mortgage news from external APIs."""

import logging
from datetime import datetime, timedelta
from typing import Optional

import requests
from dateutil import parser as date_parser

from .base import NewsSource, NewsItem
from src.config import Config

logger = logging.getLogger(__name__)


class NewsAPISource(NewsSource):
    """
    News source that fetches from NewsAPI.org.

    Provides access to news articles from thousands of sources.
    Free tier: 100 requests/day, articles up to 1 month old.
    """

    BASE_URL = "https://newsapi.org/v2/everything"

    def __init__(
        self,
        api_key: Optional[str] = None,
        priority: str = "high",
        max_items: int = 20,
    ):
        """
        Initialize NewsAPI source.

        Args:
            api_key: NewsAPI.org API key. Uses config if not provided.
            priority: Priority level (high, medium, low)
            max_items: Maximum number of items to fetch
        """
        super().__init__("NewsAPI", priority)
        self.api_key = api_key or Config.NEWS_API_KEY
        self.max_items = max_items

    def fetch(self) -> list[NewsItem]:
        """Fetch mortgage news from NewsAPI."""
        if not self.api_key:
            logger.warning("NewsAPI key not configured, skipping")
            return []

        items = []

        # Search queries for mortgage-related news
        queries = [
            "mortgage rates",
            "housing market",
            "federal reserve interest rates",
            "home prices",
            "fannie mae OR freddie mac",
        ]

        for query in queries:
            try:
                new_items = self._fetch_query(query)
                items.extend(new_items)
            except Exception as e:
                logger.error(f"Error fetching NewsAPI query '{query}': {e}")

        # Deduplicate by URL
        seen_urls = set()
        unique_items = []
        for item in items:
            if item.url not in seen_urls:
                seen_urls.add(item.url)
                unique_items.append(self._apply_priority_score(item))

        logger.info(f"Fetched {len(unique_items)} unique items from NewsAPI")
        return unique_items[:self.max_items]

    def _fetch_query(self, query: str) -> list[NewsItem]:
        """Fetch articles for a specific query."""
        # Only fetch articles from the last 7 days
        from_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

        params = {
            "q": query,
            "apiKey": self.api_key,
            "language": "en",
            "sortBy": "publishedAt",
            "from": from_date,
            "pageSize": 10,
        }

        response = requests.get(self.BASE_URL, params=params, timeout=30)
        response.raise_for_status()

        data = response.json()

        if data.get("status") != "ok":
            logger.error(f"NewsAPI error: {data.get('message', 'Unknown error')}")
            return []

        items = []
        for article in data.get("articles", []):
            item = self._parse_article(article)
            if item:
                items.append(item)

        return items

    def _parse_article(self, article: dict) -> Optional[NewsItem]:
        """Parse a NewsAPI article into a NewsItem."""
        try:
            url = article.get("url", "")
            title = article.get("title", "")

            if not url or not title or title == "[Removed]":
                return None

            # Parse published date
            published_at = None
            if article.get("publishedAt"):
                try:
                    published_at = date_parser.parse(article["publishedAt"])
                except Exception:
                    pass

            # Get source name
            source_name = "NewsAPI"
            if article.get("source", {}).get("name"):
                source_name = f"NewsAPI: {article['source']['name']}"

            return NewsItem(
                url=url,
                title=title,
                source=source_name,
                summary=article.get("description"),
                published_at=published_at,
                author=article.get("author"),
            )

        except Exception as e:
            logger.warning(f"Error parsing NewsAPI article: {e}")
            return None


class GNewsSource(NewsSource):
    """
    News source that fetches from GNews API.

    Provides access to news from Google News.
    Free tier: 100 requests/day.
    """

    BASE_URL = "https://gnews.io/api/v4/search"

    def __init__(
        self,
        api_key: Optional[str] = None,
        priority: str = "high",
        max_items: int = 20,
    ):
        """
        Initialize GNews source.

        Args:
            api_key: GNews API key. Uses config if not provided.
            priority: Priority level (high, medium, low)
            max_items: Maximum number of items to fetch
        """
        super().__init__("GNews", priority)
        self.api_key = api_key or Config.GNEWS_API_KEY
        self.max_items = max_items

    def fetch(self) -> list[NewsItem]:
        """Fetch mortgage news from GNews."""
        if not self.api_key:
            logger.warning("GNews API key not configured, skipping")
            return []

        items = []

        # Search queries for mortgage-related news
        queries = [
            "mortgage rates",
            "housing market news",
            "federal reserve rates",
            "home prices housing",
        ]

        for query in queries:
            try:
                new_items = self._fetch_query(query)
                items.extend(new_items)
            except Exception as e:
                logger.error(f"Error fetching GNews query '{query}': {e}")

        # Deduplicate by URL
        seen_urls = set()
        unique_items = []
        for item in items:
            if item.url not in seen_urls:
                seen_urls.add(item.url)
                unique_items.append(self._apply_priority_score(item))

        logger.info(f"Fetched {len(unique_items)} unique items from GNews")
        return unique_items[:self.max_items]

    def _fetch_query(self, query: str) -> list[NewsItem]:
        """Fetch articles for a specific query."""
        params = {
            "q": query,
            "token": self.api_key,
            "lang": "en",
            "country": "us",
            "max": 10,
        }

        response = requests.get(self.BASE_URL, params=params, timeout=30)
        response.raise_for_status()

        data = response.json()

        if "articles" not in data:
            logger.error(f"GNews error: {data.get('errors', 'Unknown error')}")
            return []

        items = []
        for article in data.get("articles", []):
            item = self._parse_article(article)
            if item:
                items.append(item)

        return items

    def _parse_article(self, article: dict) -> Optional[NewsItem]:
        """Parse a GNews article into a NewsItem."""
        try:
            url = article.get("url", "")
            title = article.get("title", "")

            if not url or not title:
                return None

            # Parse published date
            published_at = None
            if article.get("publishedAt"):
                try:
                    published_at = date_parser.parse(article["publishedAt"])
                except Exception:
                    pass

            # Get source name
            source_name = "GNews"
            if article.get("source", {}).get("name"):
                source_name = f"GNews: {article['source']['name']}"

            return NewsItem(
                url=url,
                title=title,
                source=source_name,
                summary=article.get("description"),
                published_at=published_at,
            )

        except Exception as e:
            logger.warning(f"Error parsing GNews article: {e}")
            return None
