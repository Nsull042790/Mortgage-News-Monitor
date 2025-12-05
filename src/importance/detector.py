"""Importance detector for identifying breaking and important mortgage news."""

import logging
import re
from datetime import datetime, timedelta
from typing import Optional

from src.news_sources.base import NewsItem
from src.config import BREAKING_NEWS_KEYWORDS, URGENT_KEYWORDS

logger = logging.getLogger(__name__)


class ImportanceDetector:
    """
    Detects the importance level of mortgage news articles.

    Breaking news alerts ONLY trigger for major events like:
    - Loan limit changes
    - Fed rate decisions
    - Major policy announcements
    - Crisis-level events
    """

    def __init__(
        self,
        breaking_keywords: Optional[list[str]] = None,
        urgent_keywords: Optional[list[str]] = None,
        breaking_threshold: int = 100,  # HIGH threshold - must have urgent keyword
        urgent_threshold: int = 150,
    ):
        self.breaking_keywords = breaking_keywords or BREAKING_NEWS_KEYWORDS
        self.urgent_keywords = urgent_keywords or URGENT_KEYWORDS
        self.breaking_threshold = breaking_threshold
        self.urgent_threshold = urgent_threshold

        # Compile regex patterns for faster matching
        self._breaking_patterns = [
            re.compile(rf"\b{re.escape(kw)}\b", re.IGNORECASE)
            for kw in self.breaking_keywords
        ]
        self._urgent_patterns = [
            re.compile(rf"\b{re.escape(kw)}\b", re.IGNORECASE)
            for kw in self.urgent_keywords
        ]

        logger.info(
            f"ImportanceDetector initialized with {len(self.urgent_keywords)} urgent keywords"
        )

    def analyze(self, item: NewsItem) -> NewsItem:
        """
        Analyze a news item and update its importance score.

        Breaking news ONLY triggers if an URGENT keyword is found.
        """
        score = item.importance_score  # Start with existing score (from source priority)
        has_urgent_keyword = False

        # Combine title and summary for analysis
        text = f"{item.title} {item.summary or ''}"

        # Check for basic relevance keywords (minor score boost for digest ranking)
        breaking_matches = self._count_keyword_matches(text, self._breaking_patterns)
        score += breaking_matches * 5  # Small boost for relevance

        # Check for URGENT keywords - these are what trigger breaking alerts
        urgent_matches = self._count_keyword_matches(text, self._urgent_patterns)
        if urgent_matches > 0:
            has_urgent_keyword = True
            score += urgent_matches * 50  # Big boost for urgent keywords

        # Bonus for recency (only matters if urgent keyword found)
        if item.published_at and has_urgent_keyword:
            try:
                now = datetime.now()
                published = item.published_at

                if published.tzinfo is not None:
                    published = published.replace(tzinfo=None)

                hours_old = (now - published).total_seconds() / 3600
                if hours_old < 1:
                    score += 30  # Recent news bonus
                elif hours_old < 6:
                    score += 15
            except Exception:
                pass

        # Bonus for official government sources (only if urgent keyword found)
        if has_urgent_keyword:
            official_sources = [
                "federal reserve",
                "fhfa",
                "hud",
                "cfpb",
            ]
            for source in official_sources:
                if source in item.source.lower():
                    score += 25
                    break

        # Update the item
        item.importance_score = score

        # ONLY mark as breaking if urgent keyword was found AND score is high enough
        item.is_breaking_news = has_urgent_keyword and score >= self.breaking_threshold

        if item.is_breaking_news:
            logger.info(f"BREAKING news detected (score={score}): {item.title[:50]}...")

        return item

    def analyze_batch(self, items: list[NewsItem]) -> list[NewsItem]:
        """Analyze a batch of news items."""
        analyzed = [self.analyze(item) for item in items]
        analyzed.sort(key=lambda x: -x.importance_score)

        breaking_count = sum(1 for item in analyzed if item.is_breaking_news)
        logger.info(
            f"Analyzed {len(analyzed)} items, {breaking_count} marked as breaking news"
        )

        return analyzed

    def filter_breaking_news(self, items: list[NewsItem]) -> list[NewsItem]:
        """Filter items to only include breaking news."""
        return [item for item in items if item.is_breaking_news]

    def filter_urgent_news(self, items: list[NewsItem]) -> list[NewsItem]:
        """Filter items to only include urgent news (highest priority)."""
        return [item for item in items if item.importance_score >= self.urgent_threshold]

    def _count_keyword_matches(
        self, text: str, patterns: list[re.Pattern]
    ) -> int:
        """Count how many keyword patterns match in the text."""
        count = 0
        for pattern in patterns:
            if pattern.search(text):
                count += 1
        return count

    def get_importance_level(self, score: int) -> str:
        """Get a human-readable importance level for a score."""
        if score >= self.urgent_threshold:
            return "URGENT"
        elif score >= self.breaking_threshold:
            return "BREAKING"
        elif score >= 30:
            return "HIGH"
        elif score >= 20:
            return "MEDIUM"
        else:
            return "LOW"
