"""RSS feed news source implementation."""

import logging
from datetime import datetime
from typing import Optional
from time import mktime

import feedparser
from dateutil import parser as date_parser

from .base import NewsSource, NewsItem

logger = logging.getLogger(__name__)


class RSSFeedSource(NewsSource):
    """News source that fetches from RSS/Atom feeds."""

    def __init__(
        self,
        name: str,
        url: str,
        priority: str = "medium",
        max_items: int = 20,
    ):
        """
        Initialize RSS feed source.

        Args:
            name: Human-readable name of the feed
            url: RSS feed URL
            priority: Priority level (high, medium, low)
            max_items: Maximum number of items to fetch
        """
        super().__init__(name, priority)
        self.url = url
        self.max_items = max_items

    def fetch(self) -> list[NewsItem]:
        """Fetch news items from RSS feed."""
        items = []

        try:
            logger.info(f"Fetching RSS feed: {self.name} ({self.url})")
            feed = feedparser.parse(self.url)

            if feed.bozo and feed.bozo_exception:
                logger.warning(
                    f"Feed parsing warning for {self.name}: {feed.bozo_exception}"
                )

            for entry in feed.entries[: self.max_items]:
                item = self._parse_entry(entry)
                if item:
                    item = self._apply_priority_score(item)
                    items.append(item)

            logger.info(f"Fetched {len(items)} items from {self.name}")

        except Exception as e:
            logger.error(f"Error fetching RSS feed {self.name}: {e}")

        return items

    def _parse_entry(self, entry: dict) -> Optional[NewsItem]:
        """Parse a single RSS feed entry into a NewsItem."""
        try:
            # Get URL
            url = entry.get("link", "")
            if not url:
                return None

            # Get title
            title = entry.get("title", "")
            if not title:
                return None

            # Get summary/description
            summary = None
            if "summary" in entry:
                summary = self._clean_html(entry.summary)
            elif "description" in entry:
                summary = self._clean_html(entry.description)

            # Get published date
            published_at = self._parse_date(entry)

            # Get author
            author = entry.get("author", None)

            # Get categories/tags
            categories = []
            if "tags" in entry:
                categories = [tag.get("term", "") for tag in entry.tags if tag.get("term")]

            return NewsItem(
                url=url,
                title=title,
                source=self.name,
                summary=summary,
                published_at=published_at,
                author=author,
                categories=categories,
            )

        except Exception as e:
            logger.warning(f"Error parsing entry from {self.name}: {e}")
            return None

    def _parse_date(self, entry: dict) -> Optional[datetime]:
        """Parse the publication date from an entry."""
        try:
            # Try parsed date first
            if "published_parsed" in entry and entry.published_parsed:
                return datetime.fromtimestamp(mktime(entry.published_parsed))

            if "updated_parsed" in entry and entry.updated_parsed:
                return datetime.fromtimestamp(mktime(entry.updated_parsed))

            # Try string dates
            for field in ["published", "updated", "created"]:
                if field in entry and entry[field]:
                    try:
                        return date_parser.parse(entry[field])
                    except Exception:
                        continue

        except Exception as e:
            logger.debug(f"Could not parse date: {e}")

        return None

    def _clean_html(self, text: str) -> str:
        """Remove HTML tags and clean up text."""
        if not text:
            return ""

        try:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(text, "lxml")
            clean_text = soup.get_text(separator=" ", strip=True)
            # Truncate long summaries
            if len(clean_text) > 500:
                clean_text = clean_text[:497] + "..."
            return clean_text
        except Exception:
            # Fallback: basic tag removal
            import re

            clean = re.sub(r"<[^>]+>", "", text)
            clean = " ".join(clean.split())
            if len(clean) > 500:
                clean = clean[:497] + "..."
            return clean
