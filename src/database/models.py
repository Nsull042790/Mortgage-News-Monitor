"""Database models and operations for Mortgage News Monitor."""

import hashlib
import logging
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy import create_engine, Column, String, DateTime, Boolean, Integer, Text
from sqlalchemy.orm import declarative_base, sessionmaker, Session

from src.config import Config

logger = logging.getLogger(__name__)

Base = declarative_base()


class Article(Base):
    """Model representing a news article."""

    __tablename__ = "articles"

    id = Column(String(64), primary_key=True)  # SHA-256 hash of URL
    url = Column(String(2048), nullable=False, unique=True)
    title = Column(String(512), nullable=False)
    summary = Column(Text, nullable=True)
    source = Column(String(256), nullable=False)
    published_at = Column(DateTime, nullable=True)
    discovered_at = Column(DateTime, default=datetime.utcnow)
    sent_to_slack = Column(Boolean, default=False)
    sent_at = Column(DateTime, nullable=True)
    is_breaking_news = Column(Boolean, default=False)
    importance_score = Column(Integer, default=0)

    def __repr__(self) -> str:
        return f"<Article(title='{self.title[:50]}...', source='{self.source}')>"

    @staticmethod
    def generate_id(url: str) -> str:
        """Generate a unique ID from URL using SHA-256."""
        return hashlib.sha256(url.encode()).hexdigest()


class Database:
    """Database manager for article storage and retrieval."""

    def __init__(self, db_path: Optional[str] = None):
        """Initialize database connection."""
        self.db_path = db_path or Config.DATABASE_PATH
        Config.ensure_data_directory()

        self.engine = create_engine(
            f"sqlite:///{self.db_path}",
            echo=False,
            connect_args={"check_same_thread": False},
        )
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        logger.info(f"Database initialized at {self.db_path}")

    def get_session(self) -> Session:
        """Get a new database session."""
        return self.SessionLocal()

    def article_exists(self, url: str) -> bool:
        """Check if an article with the given URL already exists."""
        article_id = Article.generate_id(url)
        with self.get_session() as session:
            return session.query(Article).filter(Article.id == article_id).first() is not None

    def add_article(
        self,
        url: str,
        title: str,
        source: str,
        summary: Optional[str] = None,
        published_at: Optional[datetime] = None,
        is_breaking_news: bool = False,
        importance_score: int = 0,
    ) -> Optional[Article]:
        """Add a new article to the database if it doesn't exist."""
        if self.article_exists(url):
            logger.debug(f"Article already exists: {title[:50]}...")
            return None

        article = Article(
            id=Article.generate_id(url),
            url=url,
            title=title,
            summary=summary,
            source=source,
            published_at=published_at,
            is_breaking_news=is_breaking_news,
            importance_score=importance_score,
        )

        with self.get_session() as session:
            session.add(article)
            session.commit()
            session.refresh(article)
            logger.info(f"Added new article: {title[:50]}...")
            return article

    def mark_as_sent(self, url: str) -> bool:
        """Mark an article as sent to Slack."""
        article_id = Article.generate_id(url)
        with self.get_session() as session:
            article = session.query(Article).filter(Article.id == article_id).first()
            if article:
                article.sent_to_slack = True
                article.sent_at = datetime.utcnow()
                session.commit()
                return True
            return False

    def get_unsent_articles(
        self, breaking_only: bool = False, limit: int = 50
    ) -> list[Article]:
        """Get articles that haven't been sent to Slack yet."""
        with self.get_session() as session:
            query = session.query(Article).filter(Article.sent_to_slack == False)

            if breaking_only:
                query = query.filter(Article.is_breaking_news == True)

            return (
                query.order_by(Article.importance_score.desc(), Article.discovered_at.desc())
                .limit(limit)
                .all()
            )

    def get_articles_for_digest(self, hours: int = 24) -> list[Article]:
        """Get articles from the last N hours for daily digest."""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        with self.get_session() as session:
            return (
                session.query(Article)
                .filter(Article.discovered_at >= cutoff)
                .order_by(Article.importance_score.desc(), Article.published_at.desc())
                .all()
            )

    def get_recent_breaking_news(self, minutes: int = 30) -> list[Article]:
        """Get breaking news from the last N minutes that hasn't been sent."""
        cutoff = datetime.utcnow() - timedelta(minutes=minutes)
        with self.get_session() as session:
            return (
                session.query(Article)
                .filter(
                    Article.is_breaking_news == True,
                    Article.sent_to_slack == False,
                    Article.discovered_at >= cutoff,
                )
                .order_by(Article.importance_score.desc())
                .all()
            )

    def cleanup_old_articles(self, days: int = 30) -> int:
        """Remove articles older than N days."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        with self.get_session() as session:
            deleted = (
                session.query(Article)
                .filter(Article.discovered_at < cutoff)
                .delete()
            )
            session.commit()
            logger.info(f"Cleaned up {deleted} old articles")
            return deleted
