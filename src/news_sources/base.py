"""Base classes for news sources."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class NewsItem:
    """Represents a single news item/article."""

    url: str
    title: str
    source: str
    summary: Optional[str] = None
    published_at: Optional[datetime] = None
    author: Optional[str] = None
    categories: list[str] = field(default_factory=list)
    importance_score: int = 0
    is_breaking_news: bool = False

    def __post_init__(self):
        """Clean up data after initialization."""
        self.title = self.title.strip() if self.title else ""
        self.summary = self.summary.strip() if self.summary else None
        self.url = self.url.strip() if self.url else ""

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "url": self.url,
            "title": self.title,
            "source": self.source,
            "summary": self.summary,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "author": self.author,
            "categories": self.categories,
            "importance_score": self.importance_score,
            "is_breaking_news": self.is_breaking_news,
        }


class NewsSource(ABC):
    """Abstract base class for news sources."""

    def __init__(self, name: str, priority: str = "medium"):
        """
        Initialize news source.

        Args:
            name: Human-readable name of the source
            priority: Priority level (high, medium, low)
        """
        self.name = name
        self.priority = priority
        self._priority_score = {"high": 30, "medium": 20, "low": 10}.get(priority, 20)

    @abstractmethod
    def fetch(self) -> list[NewsItem]:
        """
        Fetch news items from the source.

        Returns:
            List of NewsItem objects
        """
        pass

    def _apply_priority_score(self, item: NewsItem) -> NewsItem:
        """Add source priority to item's importance score."""
        item.importance_score += self._priority_score
        return item
