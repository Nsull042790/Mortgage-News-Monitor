"""Scheduler for mortgage news monitoring jobs."""

import logging
from datetime import datetime
from typing import Optional, Callable

import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from src.config import Config
from src.database import Database
from src.news_sources import NewsAggregator
from src.importance import ImportanceDetector
from src.slack import SlackClient

logger = logging.getLogger(__name__)


class NewsScheduler:
    """
    Scheduler for mortgage news monitoring.

    Handles:
    - Daily digest at configured time (weekdays only)
    - Breaking news monitoring (weekdays, business hours only)
    - Database cleanup
    """

    def __init__(
        self,
        database: Optional[Database] = None,
        aggregator: Optional[NewsAggregator] = None,
        detector: Optional[ImportanceDetector] = None,
        slack_client: Optional[SlackClient] = None,
    ):
        """
        Initialize the news scheduler.

        Args:
            database: Database instance for tracking articles
            aggregator: News aggregator for fetching news
            detector: Importance detector for analyzing news
            slack_client: Slack client for sending messages
        """
        self.database = database or Database()
        self.aggregator = aggregator or NewsAggregator()
        self.detector = detector or ImportanceDetector()
        self.slack_client = slack_client or SlackClient()

        self.timezone = pytz.timezone(Config.TIMEZONE)
        self.scheduler = BackgroundScheduler(timezone=self.timezone)

        # Business hours configuration (for free tier optimization)
        self.business_hours_start = int(Config.BUSINESS_HOURS_START)
        self.business_hours_end = int(Config.BUSINESS_HOURS_END)

        self._setup_jobs()
        logger.info(f"NewsScheduler initialized with timezone {Config.TIMEZONE}")

    def _is_business_hours(self) -> bool:
        """Check if current time is within business hours on a weekday."""
        now = datetime.now(self.timezone)
        # Monday = 0, Sunday = 6
        if now.weekday() >= 5:  # Saturday or Sunday
            return False
        if now.hour < self.business_hours_start or now.hour >= self.business_hours_end:
            return False
        return True

    def _setup_jobs(self) -> None:
        """Set up all scheduled jobs."""
        # Parse daily digest time
        digest_hour, digest_minute = map(int, Config.DAILY_DIGEST_TIME.split(":"))

        # Daily digest job - weekdays at configured time
        self.scheduler.add_job(
            self._daily_digest_job,
            CronTrigger(
                day_of_week="mon-fri",
                hour=digest_hour,
                minute=digest_minute,
                timezone=self.timezone,
            ),
            id="daily_digest",
            name="Daily Mortgage News Digest",
            replace_existing=True,
        )
        logger.info(
            f"Scheduled daily digest for weekdays at {Config.DAILY_DIGEST_TIME} {Config.TIMEZONE}"
        )

        # Breaking news monitoring job - weekdays only, business hours only
        # Uses cron to only run during business hours (saves Railway free tier hours!)
        # Runs every N minutes, but only during weekday business hours
        interval = Config.BREAKING_NEWS_CHECK_INTERVAL

        # Create cron expression for every N minutes during business hours
        # e.g., "*/15" means every 15 minutes
        self.scheduler.add_job(
            self._breaking_news_job,
            CronTrigger(
                day_of_week="mon-fri",
                hour=f"{self.business_hours_start}-{self.business_hours_end - 1}",
                minute=f"*/{interval}",
                timezone=self.timezone,
            ),
            id="breaking_news",
            name="Breaking News Monitor",
            replace_existing=True,
        )
        logger.info(
            f"Scheduled breaking news check every {interval} min, "
            f"weekdays {self.business_hours_start}:00-{self.business_hours_end}:00 {Config.TIMEZONE}"
        )

        # Database cleanup job - weekdays at 3am (only if within business hours start)
        self.scheduler.add_job(
            self._cleanup_job,
            CronTrigger(
                day_of_week="mon-fri",
                hour=self.business_hours_start,
                minute=5,
                timezone=self.timezone,
            ),
            id="cleanup",
            name="Database Cleanup",
            replace_existing=True,
        )
        logger.info(f"Scheduled database cleanup for weekdays at {self.business_hours_start}:05")

    def _daily_digest_job(self) -> None:
        """Job to send the daily news digest."""
        logger.info("Running daily digest job")
        try:
            # Fetch all news (including APIs for daily digest)
            items = self.aggregator.fetch_all()

            # Analyze for importance
            items = self.detector.analyze_batch(items)

            # Store new articles in database
            for item in items:
                self.database.add_article(
                    url=item.url,
                    title=item.title,
                    source=item.source,
                    summary=item.summary,
                    published_at=item.published_at,
                    is_breaking_news=item.is_breaking_news,
                    importance_score=item.importance_score,
                )

            # Get articles from last 24 hours for digest
            digest_items = self.database.get_articles_for_digest(hours=24)

            # Convert to NewsItem objects for formatting
            news_items = []
            for article in digest_items:
                from src.news_sources.base import NewsItem

                news_item = NewsItem(
                    url=article.url,
                    title=article.title,
                    source=article.source,
                    summary=article.summary,
                    published_at=article.published_at,
                    importance_score=article.importance_score,
                    is_breaking_news=article.is_breaking_news,
                )
                news_items.append(news_item)

            # Send digest
            success = self.slack_client.send_daily_digest(news_items)

            if success:
                logger.info(f"Daily digest sent with {len(news_items)} articles")
            else:
                logger.error("Failed to send daily digest")

        except Exception as e:
            logger.error(f"Error in daily digest job: {e}", exc_info=True)

    def _breaking_news_job(self) -> None:
        """Job to check for breaking news."""
        logger.info("Running breaking news check")
        try:
            # Fetch news from RSS only (to conserve API quotas)
            items = self.aggregator.fetch_rss_only()

            # Analyze for importance
            items = self.detector.analyze_batch(items)

            # Filter for breaking news
            breaking_items = self.detector.filter_breaking_news(items)

            sent_count = 0
            for item in breaking_items:
                # Check if already in database
                if self.database.article_exists(item.url):
                    continue

                # Add to database
                self.database.add_article(
                    url=item.url,
                    title=item.title,
                    source=item.source,
                    summary=item.summary,
                    published_at=item.published_at,
                    is_breaking_news=True,
                    importance_score=item.importance_score,
                )

                # Send breaking news alert
                success = self.slack_client.send_breaking_news(item)

                if success:
                    self.database.mark_as_sent(item.url)
                    sent_count += 1
                    logger.info(f"Sent breaking news: {item.title[:50]}...")

            if sent_count > 0:
                logger.info(f"Sent {sent_count} breaking news alerts")
            else:
                logger.debug("No new breaking news found")

        except Exception as e:
            logger.error(f"Error in breaking news job: {e}", exc_info=True)

    def _cleanup_job(self) -> None:
        """Job to clean up old database entries."""
        logger.info("Running database cleanup")
        try:
            deleted = self.database.cleanup_old_articles(days=30)
            logger.info(f"Cleaned up {deleted} old articles")
        except Exception as e:
            logger.error(f"Error in cleanup job: {e}", exc_info=True)

    def start(self) -> None:
        """Start the scheduler."""
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("Scheduler started")
            logger.info(
                f"Running weekdays only, {self.business_hours_start}:00-{self.business_hours_end}:00 "
                f"(optimized for Railway free tier)"
            )

    def stop(self) -> None:
        """Stop the scheduler."""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            logger.info("Scheduler stopped")

    def run_now(self, job_id: str) -> bool:
        """
        Run a specific job immediately.

        Args:
            job_id: The job identifier (daily_digest, breaking_news, cleanup)

        Returns:
            True if job was triggered, False if not found
        """
        job = self.scheduler.get_job(job_id)
        if job:
            job.modify(next_run_time=datetime.now(self.timezone))
            logger.info(f"Triggered immediate run of job: {job_id}")
            return True
        else:
            logger.warning(f"Job not found: {job_id}")
            return False

    def get_next_run_times(self) -> dict[str, Optional[datetime]]:
        """Get the next run time for all jobs."""
        times = {}
        for job in self.scheduler.get_jobs():
            times[job.id] = job.next_run_time
        return times

    def is_running(self) -> bool:
        """Check if scheduler is running."""
        return self.scheduler.running
