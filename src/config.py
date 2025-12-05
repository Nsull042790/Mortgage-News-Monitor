"""Configuration management for Mortgage News Monitor."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Application configuration loaded from environment variables."""

    # Slack Configuration (supports both webhook and bot token)
    SLACK_WEBHOOK_URL: str = os.getenv("SLACK_WEBHOOK_URL", "")
    SLACK_BOT_TOKEN: str = os.getenv("SLACK_BOT_TOKEN", "")
    SLACK_CHANNEL_ID: str = os.getenv("SLACK_CHANNEL_ID", "")

    # Monitoring Configuration
    BREAKING_NEWS_CHECK_INTERVAL: int = int(
        os.getenv("BREAKING_NEWS_CHECK_INTERVAL", "15")
    )
    DAILY_DIGEST_TIME: str = os.getenv("DAILY_DIGEST_TIME", "08:00")
    TIMEZONE: str = os.getenv("TIMEZONE", "America/New_York")

    # Business hours (for Railway free tier optimization)
    # Only monitors during these hours on weekdays to save compute hours
    BUSINESS_HOURS_START: str = os.getenv("BUSINESS_HOURS_START", "6")   # 6 AM
    BUSINESS_HOURS_END: str = os.getenv("BUSINESS_HOURS_END", "20")      # 8 PM

    # Database
    DATABASE_PATH: str = os.getenv("DATABASE_PATH", "./data/mortgage_news.db")

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # News APIs
    NEWS_API_KEY: str = os.getenv("NEWS_API_KEY", "")
    GNEWS_API_KEY: str = os.getenv("GNEWS_API_KEY", "")

    @classmethod
    def validate(cls) -> list[str]:
        """Validate required configuration values."""
        errors = []

        if not cls.SLACK_WEBHOOK_URL and not cls.SLACK_BOT_TOKEN:
            errors.append("Either SLACK_WEBHOOK_URL or SLACK_BOT_TOKEN is required")

        if cls.SLACK_BOT_TOKEN and not cls.SLACK_CHANNEL_ID:
            errors.append("SLACK_CHANNEL_ID is required when using SLACK_BOT_TOKEN")

        return errors

    @classmethod
    def ensure_data_directory(cls) -> None:
        """Ensure the data directory exists."""
        db_path = Path(cls.DATABASE_PATH)
        db_path.parent.mkdir(parents=True, exist_ok=True)

    @classmethod
    def use_webhook(cls) -> bool:
        """Check if webhook should be used (preferred over bot token)."""
        return bool(cls.SLACK_WEBHOOK_URL)


# Mortgage news RSS feeds to monitor
MORTGAGE_RSS_FEEDS = [
    # Primary Mortgage News Sources
    {
        "name": "Mortgage News Daily",
        "url": "https://www.mortgagenewsdaily.com/rss/mortgage-news",
        "priority": "high",
    },
    {
        "name": "HousingWire",
        "url": "https://www.housingwire.com/feed/",
        "priority": "high",
    },
    {
        "name": "National Mortgage News",
        "url": "https://www.nationalmortgagenews.com/feed",
        "priority": "high",
    },
    # Government and Regulatory Agencies
    {
        "name": "FHFA News",
        "url": "https://www.fhfa.gov/rss/FHFANews.xml",
        "priority": "high",
    },
    {
        "name": "FHFA Speeches",
        "url": "https://www.fhfa.gov/rss/Speeches.xml",
        "priority": "medium",
    },
    {
        "name": "HUD News",
        "url": "https://www.hud.gov/rss/hud_news.xml",
        "priority": "high",
    },
    {
        "name": "Federal Reserve Press Releases",
        "url": "https://www.federalreserve.gov/feeds/press_all.xml",
        "priority": "high",
    },
    {
        "name": "CFPB Newsroom",
        "url": "https://www.consumerfinance.gov/about-us/newsroom/feed/",
        "priority": "high",
    },
    # GSEs and Industry Organizations
    {
        "name": "Fannie Mae News",
        "url": "https://www.fanniemae.com/rss/news-releases",
        "priority": "high",
    },
    {
        "name": "Freddie Mac News",
        "url": "https://www.freddiemac.com/rss/news_releases.xml",
        "priority": "high",
    },
    {
        "name": "Mortgage Bankers Association",
        "url": "https://www.mba.org/news-and-research/newsroom/rss",
        "priority": "high",
    },
    # Real Estate and Housing News
    {
        "name": "Inman News",
        "url": "https://www.inman.com/feed/",
        "priority": "medium",
    },
    {
        "name": "RealtyTrac",
        "url": "https://www.realtytrac.com/news/feed/",
        "priority": "medium",
    },
    {
        "name": "Zillow Research",
        "url": "https://www.zillow.com/research/feed/",
        "priority": "medium",
    },
    # Financial News
    {
        "name": "CNBC Real Estate",
        "url": "https://www.cnbc.com/id/10000115/device/rss/rss.html",
        "priority": "medium",
    },
    {
        "name": "MarketWatch Real Estate",
        "url": "https://feeds.marketwatch.com/marketwatch/realestate/",
        "priority": "medium",
    },
    {
        "name": "Reuters Business",
        "url": "https://www.reutersagency.com/feed/?taxonomy=best-sectors&post_type=best",
        "priority": "low",
    },
    # Specialized Mortgage Sources
    {
        "name": "The Mortgage Reports",
        "url": "https://themortgagereports.com/feed",
        "priority": "medium",
    },
    {
        "name": "Scotsman Guide",
        "url": "https://www.scotsmanguide.com/feed/",
        "priority": "medium",
    },
]

# Keywords for daily digest relevance (used for scoring, not breaking alerts)
BREAKING_NEWS_KEYWORDS = [
    # These add minor score - help rank articles in digest
    "mortgage rate",
    "interest rate",
    "housing market",
    "home prices",
    "fannie mae",
    "freddie mac",
    "fha",
    "fhfa",
]

# URGENT: Only these trigger breaking news alerts
# Must be MAJOR policy/rate changes - not routine news
URGENT_KEYWORDS = [
    # Loan limits (annual announcement)
    "loan limit increase",
    "loan limit change",
    "conforming loan limit",
    "new loan limits",
    "2024 loan limits",
    "2025 loan limits",
    "2026 loan limits",
    # Fed rate decisions (actual changes only)
    "fed cuts rates",
    "fed raises rates",
    "fed holds rates",
    "rate cut announced",
    "rate hike announced",
    "fomc decision",
    "basis point cut",
    "basis point hike",
    # Major policy changes
    "fhfa announces",
    "hud announces",
    "cfpb announces",
    "new regulation",
    "rule change",
    "policy change",
    # Crisis-level events only
    "mortgage crisis",
    "housing crisis",
    "lending freeze",
    "market crash",
    "emergency action",
]
