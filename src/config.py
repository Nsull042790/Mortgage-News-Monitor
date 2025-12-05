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

# Keywords that indicate breaking/important mortgage news
BREAKING_NEWS_KEYWORDS = [
    # Federal Reserve and rates
    "federal reserve",
    "fed rate",
    "interest rate cut",
    "interest rate hike",
    "rate decision",
    "fomc",
    "powell",
    "rate announcement",
    "basis points",
    "rate change",
    "monetary policy",
    "quantitative easing",
    "quantitative tightening",
    # Mortgage rates
    "mortgage rate",
    "30-year rate",
    "15-year rate",
    "rate drop",
    "rate surge",
    "record low",
    "record high",
    "mortgage rates fall",
    "mortgage rates rise",
    "rates plunge",
    "rates spike",
    "average rate",
    "conforming loan",
    "jumbo loan",
    # Market events
    "housing crisis",
    "mortgage crisis",
    "foreclosure",
    "housing market crash",
    "real estate crash",
    "lending freeze",
    "credit crunch",
    "default rate",
    "delinquency",
    # Policy and regulation
    "fha",
    "fannie mae",
    "freddie mac",
    "ginnie mae",
    "fhfa",
    "cfpb",
    "hud",
    "housing policy",
    "mortgage regulation",
    "down payment assistance",
    "first-time homebuyer",
    "loan limit",
    "conforming limit",
    "qm rule",
    "qualified mortgage",
    "ability to repay",
    "gse reform",
    # Economic indicators
    "housing starts",
    "home sales",
    "pending home sales",
    "existing home sales",
    "new home sales",
    "housing inventory",
    "home prices",
    "case-shiller",
    "home price index",
    "affordability",
    "housing supply",
    "building permits",
    "construction spending",
]

# High-priority keywords that should trigger immediate alerts
URGENT_KEYWORDS = [
    "breaking",
    "just announced",
    "emergency",
    "fed rate",
    "rate decision",
    "rate cut",
    "rate hike",
    "fomc announcement",
    "powell announces",
    "mortgage rates plunge",
    "mortgage rates surge",
    "record low",
    "record high",
    "crisis",
    "crash",
    "halt",
    "suspend",
    "freeze",
    "emergency action",
    "historic",
    "unprecedented",
]
