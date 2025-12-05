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

    Uses keyword matching and source priority to determine if news
    is breaking/urgent and should be sent immediately.
    """

    def __init__(
        self,
        breaking_keywords: Optional[list[str]] = None,
        urgent_keywords: Optional[list[str]] = None,
        breaking_threshold: int = 50,
        urgent_threshold: int = 80,
    ):
        """
        Initialize the importance detector.

        Args:
            breaking_keywords: Keywords that indicate important news (adds score)
            urgent_keywords: Keywords that indicate urgent/breaking news (adds more score)
            breaking_threshold: Minimum score to be considered breaking news
            urgent_threshold: Minimum score to be considered urgent (immediate alert)
        """
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
            f"ImportanceDetector initialized with {len(self.breaking_keywords)} breaking "
            f"and {len(self.urgent_keywords)} urgent keywords"
        )

    def analyze(self, item: NewsItem) -> NewsItem:
        """
        Analyze a news item and update its importance score.

        Args:
            item: The news item to analyze

        Returns:
            The same NewsItem with updated importance_score and is_breaking_news
        """
        score = item.importance_score  # Start with existing score (from source priority)

        # Combine title and summary for analysis
        text = f"{item.title} {item.summary or ''}"

        # Check for breaking keywords
        breaking_matches = self._count_keyword_matches(text, self._breaking_patterns)
        score += breaking_matches * 10  # 10 points per breaking keyword

        # Check for urgent keywords (higher value)
        urgent_matches = self._count_keyword_matches(text, self._urgent_patterns)
        score += urgent_matches * 20  # 20 points per urgent keyword

        # Bonus for recency (news from last hour gets bonus)
        if item.published_at:
            hours_old = (datetime.now() - item.published_at).total_seconds() / 3600
            if hours_old < 1:
                score += 30  # Recent news bonus
            elif hours_old < 6:
                score += 15
            elif hours_old < 24:
                score += 5

        # Check for high-priority sources in the item source name
        high_priority_sources = [
            "federal reserve",
            "fhfa",
            "hud",
            "cfpb",
            "fannie mae",
            "freddie mac",
            "fomc",
        ]
        for source in high_priority_sources:
            if source in item.source.lower():
                score += 15
                break

        # Update the item
        item.importance_score = score
        item.is_breaking_news = score >= self.breaking_threshold

        if score >= self.urgent_threshold:
            logger.info(f"URGENT news detected (score={score}): {item.title[:50]}...")
        elif item.is_breaking_news:
            logger.info(f"Breaking news detected (score={score}): {item.title[:50]}...")

        return item

    def analyze_batch(self, items: list[NewsItem]) -> list[NewsItem]:
        """
        Analyze a batch of news items.

        Args:
            items: List of news items to analyze

        Returns:
            List of items with updated importance scores
        """
        analyzed = [self.analyze(item) for item in items]

        # Sort by importance
        analyzed.sort(key=lambda x: -x.importance_score)

        breaking_count = sum(1 for item in analyzed if item.is_breaking_news)
        logger.info(
            f"Analyzed {len(analyzed)} items, {breaking_count} marked as breaking news"
        )

        return analyzed

    def filter_breaking_news(self, items: list[NewsItem]) -> list[NewsItem]:
        """
        Filter items to only include breaking news.

        Args:
            items: List of news items (should already be analyzed)

        Returns:
            List of items that meet the breaking news threshold
        """
        return [item for item in items if item.is_breaking_news]

    def filter_urgent_news(self, items: list[NewsItem]) -> list[NewsItem]:
        """
        Filter items to only include urgent news (highest priority).

        Args:
            items: List of news items (should already be analyzed)

        Returns:
            List of items that meet the urgent threshold
        """
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
        """
        Get a human-readable importance level for a score.

        Args:
            score: The importance score

        Returns:
            String describing the importance level
        """
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
