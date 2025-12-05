#!/usr/bin/env python3
"""
Mortgage News Monitor - Main Application Entry Point

A Slack-integrated mortgage news monitoring application that:
- Sends daily digests every weekday at 8am
- Monitors for breaking/important mortgage news continuously
- Supports RSS feeds, NewsAPI, and GNews
"""

import argparse
import logging
import signal
import sys
import time
from datetime import datetime

from src.config import Config
from src.database import Database
from src.news_sources import NewsAggregator
from src.importance import ImportanceDetector
from src.slack import SlackClient
from src.scheduler import NewsScheduler


def setup_logging(level: str = "INFO") -> None:
    """Set up logging configuration."""
    log_level = getattr(logging, level.upper(), logging.INFO)

    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Set up console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(console_handler)

    # Reduce noise from third-party libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("apscheduler").setLevel(logging.WARNING)


def validate_config() -> bool:
    """Validate configuration and return True if valid."""
    errors = Config.validate()
    if errors:
        for error in errors:
            logging.error(f"Configuration error: {error}")
        return False
    return True


def run_monitor() -> None:
    """Run the continuous monitoring service."""
    logger = logging.getLogger(__name__)
    logger.info("Starting Mortgage News Monitor...")

    # Initialize components
    database = Database()
    aggregator = NewsAggregator()
    detector = ImportanceDetector()
    slack_client = SlackClient()

    # Test Slack connection
    logger.info("Testing Slack connection...")
    if not slack_client.test_connection():
        logger.error("Failed to connect to Slack. Check your configuration.")
        sys.exit(1)

    logger.info("Slack connection successful!")

    # Create scheduler
    scheduler = NewsScheduler(
        database=database,
        aggregator=aggregator,
        detector=detector,
        slack_client=slack_client,
    )

    # Handle shutdown gracefully
    def signal_handler(signum, frame):
        logger.info("Shutdown signal received, stopping scheduler...")
        scheduler.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Start scheduler
    scheduler.start()

    # Print next run times
    next_runs = scheduler.get_next_run_times()
    logger.info("Scheduled jobs:")
    for job_id, next_run in next_runs.items():
        if next_run:
            logger.info(f"  - {job_id}: {next_run.strftime('%Y-%m-%d %H:%M:%S %Z')}")

    logger.info("Monitor is running. Press Ctrl+C to stop.")

    # Keep the main thread alive
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        scheduler.stop()


def run_digest_now() -> None:
    """Run the daily digest immediately."""
    logger = logging.getLogger(__name__)
    logger.info("Running daily digest now...")

    database = Database()
    aggregator = NewsAggregator()
    detector = ImportanceDetector()
    slack_client = SlackClient()

    # Fetch news
    logger.info("Fetching news from all sources...")
    items = aggregator.fetch_all()
    logger.info(f"Fetched {len(items)} articles")

    # Analyze
    items = detector.analyze_batch(items)

    # Store in database
    for item in items:
        database.add_article(
            url=item.url,
            title=item.title,
            source=item.source,
            summary=item.summary,
            published_at=item.published_at,
            is_breaking_news=item.is_breaking_news,
            importance_score=item.importance_score,
        )

    # Send digest
    success = slack_client.send_daily_digest(items[:15])  # Top 15 stories

    if success:
        logger.info("Daily digest sent successfully!")
    else:
        logger.error("Failed to send daily digest")
        sys.exit(1)


def check_breaking_news() -> None:
    """Check for breaking news immediately."""
    logger = logging.getLogger(__name__)
    logger.info("Checking for breaking news...")

    database = Database()
    aggregator = NewsAggregator()
    detector = ImportanceDetector()
    slack_client = SlackClient()

    # Fetch news from RSS (conserve API quotas)
    items = aggregator.fetch_rss_only()
    logger.info(f"Fetched {len(items)} articles from RSS feeds")

    # Analyze
    items = detector.analyze_batch(items)

    # Filter breaking news
    breaking_items = detector.filter_breaking_news(items)
    logger.info(f"Found {len(breaking_items)} breaking news articles")

    sent_count = 0
    for item in breaking_items:
        if database.article_exists(item.url):
            logger.debug(f"Skipping (already exists): {item.title[:50]}...")
            continue

        # Add to database
        database.add_article(
            url=item.url,
            title=item.title,
            source=item.source,
            summary=item.summary,
            published_at=item.published_at,
            is_breaking_news=True,
            importance_score=item.importance_score,
        )

        # Send alert
        success = slack_client.send_breaking_news(item)
        if success:
            database.mark_as_sent(item.url)
            sent_count += 1
            logger.info(f"Sent: {item.title[:50]}...")

    logger.info(f"Sent {sent_count} breaking news alerts")


def list_sources() -> None:
    """List all configured news sources."""
    aggregator = NewsAggregator()
    sources = aggregator.list_sources()

    print("\nConfigured News Sources:")
    print("-" * 60)
    for i, source in enumerate(sources, 1):
        print(f"{i:2}. {source['name']}")
        print(f"    Type: {source['type']}, Priority: {source['priority']}")
    print(f"\nTotal: {len(sources)} sources")


def test_fetch() -> None:
    """Test fetching news without sending to Slack."""
    logger = logging.getLogger(__name__)
    logger.info("Testing news fetch...")

    aggregator = NewsAggregator()
    detector = ImportanceDetector()

    # Fetch
    items = aggregator.fetch_all()
    logger.info(f"Fetched {len(items)} articles")

    # Analyze
    items = detector.analyze_batch(items)

    # Print results
    print("\n" + "=" * 80)
    print("TOP NEWS ARTICLES")
    print("=" * 80)

    for i, item in enumerate(items[:20], 1):
        importance = detector.get_importance_level(item.importance_score)
        breaking = " [BREAKING]" if item.is_breaking_news else ""
        print(f"\n{i}. [{importance}]{breaking} {item.title}")
        print(f"   Source: {item.source}")
        print(f"   Score: {item.importance_score}")
        if item.published_at:
            print(f"   Published: {item.published_at.strftime('%Y-%m-%d %H:%M')}")
        print(f"   URL: {item.url}")


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Mortgage News Monitor - Slack-integrated mortgage news monitoring",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  run         Start the continuous monitoring service
  digest      Send the daily digest immediately
  breaking    Check for breaking news immediately
  sources     List all configured news sources
  test        Test fetching news (no Slack)

Examples:
  %(prog)s run              # Start the monitor
  %(prog)s digest           # Send digest now
  %(prog)s breaking         # Check breaking news
  %(prog)s test             # Test without Slack
        """,
    )

    parser.add_argument(
        "command",
        choices=["run", "digest", "breaking", "sources", "test"],
        help="Command to execute",
    )

    parser.add_argument(
        "--log-level",
        default=Config.LOG_LEVEL,
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level (default: %(default)s)",
    )

    args = parser.parse_args()

    # Set up logging
    setup_logging(args.log_level)

    # Validate config for commands that need Slack
    if args.command in ["run", "digest", "breaking"]:
        if not validate_config():
            sys.exit(1)

    # Execute command
    if args.command == "run":
        run_monitor()
    elif args.command == "digest":
        run_digest_now()
    elif args.command == "breaking":
        check_breaking_news()
    elif args.command == "sources":
        list_sources()
    elif args.command == "test":
        test_fetch()


if __name__ == "__main__":
    main()
