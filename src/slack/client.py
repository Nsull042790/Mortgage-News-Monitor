"""Slack client for sending mortgage news alerts."""

import json
import logging
from datetime import datetime
from typing import Optional

import requests
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from src.config import Config
from src.news_sources.base import NewsItem

logger = logging.getLogger(__name__)


class SlackClient:
    """Client for sending mortgage news to Slack via webhook or bot token."""

    def __init__(
        self,
        webhook_url: Optional[str] = None,
        token: Optional[str] = None,
        channel: Optional[str] = None,
    ):
        """
        Initialize Slack client.

        Args:
            webhook_url: Slack webhook URL (preferred method)
            token: Slack bot token (alternative to webhook)
            channel: Default channel ID (required for bot token)
        """
        self.webhook_url = webhook_url or Config.SLACK_WEBHOOK_URL
        self.token = token or Config.SLACK_BOT_TOKEN
        self.channel = channel or Config.SLACK_CHANNEL_ID

        # Determine which method to use
        self.use_webhook = bool(self.webhook_url)

        if not self.use_webhook and self.token:
            self.client = WebClient(token=self.token)
        else:
            self.client = None

        logger.info(
            f"Slack client initialized using {'webhook' if self.use_webhook else 'bot token'}"
        )

    def test_connection(self) -> bool:
        """Test the Slack connection."""
        try:
            if self.use_webhook:
                # Send a test message via webhook
                response = requests.post(
                    self.webhook_url,
                    json={"text": "Mortgage News Monitor connection test successful!"},
                    timeout=10,
                )
                if response.status_code == 200:
                    logger.info("Webhook connection test successful")
                    return True
                else:
                    logger.error(f"Webhook test failed: {response.status_code}")
                    return False
            else:
                response = self.client.auth_test()
                logger.info(f"Connected to Slack as {response['user']}")
                return True
        except Exception as e:
            logger.error(f"Failed to connect to Slack: {e}")
            return False

    def _send_webhook(self, payload: dict) -> bool:
        """Send a message via webhook."""
        try:
            response = requests.post(
                self.webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30,
            )
            if response.status_code == 200:
                return True
            else:
                logger.error(f"Webhook request failed: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"Webhook request error: {e}")
            return False

    def _send_api(self, text: str, blocks: list[dict], channel: Optional[str] = None) -> bool:
        """Send a message via Slack API."""
        target_channel = channel or self.channel
        try:
            response = self.client.chat_postMessage(
                channel=target_channel,
                text=text,
                blocks=blocks,
                unfurl_links=False,
                unfurl_media=False,
            )
            return True
        except SlackApiError as e:
            logger.error(f"Slack API error: {e.response['error']}")
            return False

    def send_breaking_news(
        self,
        item: NewsItem,
        channel: Optional[str] = None,
    ) -> bool:
        """
        Send a breaking news alert.

        Args:
            item: The news item to send
            channel: Override channel (uses default if not provided)

        Returns:
            True if sent successfully, False otherwise
        """
        blocks = self._format_breaking_news_blocks(item)
        text = f"🚨 BREAKING: {item.title}"

        if self.use_webhook:
            payload = {"text": text, "blocks": blocks}
            success = self._send_webhook(payload)
        else:
            success = self._send_api(text, blocks, channel)

        if success:
            logger.info(f"Sent breaking news alert: {item.title[:50]}...")

        return success

    def send_news_item(
        self,
        item: NewsItem,
        channel: Optional[str] = None,
    ) -> bool:
        """
        Send a single news item.

        Args:
            item: The news item to send
            channel: Override channel (uses default if not provided)

        Returns:
            True if sent successfully, False otherwise
        """
        blocks = self._format_news_item_blocks(item)
        text = f"📰 {item.title}"

        if self.use_webhook:
            payload = {"text": text, "blocks": blocks}
            success = self._send_webhook(payload)
        else:
            success = self._send_api(text, blocks, channel)

        if success:
            logger.info(f"Sent news item: {item.title[:50]}...")

        return success

    def send_daily_digest(
        self,
        items: list[NewsItem],
        channel: Optional[str] = None,
    ) -> bool:
        """
        Send the daily mortgage news digest.

        Args:
            items: List of news items for the digest
            channel: Override channel (uses default if not provided)

        Returns:
            True if sent successfully, False otherwise
        """
        if not items:
            logger.info("No items for daily digest, sending notification")
            return self._send_empty_digest(channel)

        blocks = self._format_daily_digest_blocks(items)
        text = f"📊 Daily Mortgage News Digest - {len(items)} stories"

        if self.use_webhook:
            payload = {"text": text, "blocks": blocks}
            success = self._send_webhook(payload)
        else:
            success = self._send_api(text, blocks, channel)

        if success:
            logger.info(f"Sent daily digest with {len(items)} items")

        return success

    def _send_empty_digest(self, channel: Optional[str] = None) -> bool:
        """Send notification when no news is available."""
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "📊 Daily Mortgage News Digest",
                    "emoji": True,
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "_No significant mortgage news in the last 24 hours._",
                },
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"Generated at {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                    }
                ],
            },
        ]
        text = "📊 Daily Mortgage News Digest - No news today"

        if self.use_webhook:
            return self._send_webhook({"text": text, "blocks": blocks})
        else:
            return self._send_api(text, blocks, channel)

    def _format_breaking_news_blocks(self, item: NewsItem) -> list[dict]:
        """Format blocks for breaking news alert."""
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "🚨 BREAKING MORTGAGE NEWS",
                    "emoji": True,
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*<{item.url}|{item.title}>*",
                },
            },
        ]

        if item.summary:
            blocks.append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": item.summary[:300] + ("..." if len(item.summary) > 300 else ""),
                    },
                }
            )

        context_parts = [f"Source: {item.source}"]
        if item.published_at:
            context_parts.append(f"Published: {item.published_at.strftime('%Y-%m-%d %H:%M')}")

        blocks.append(
            {
                "type": "context",
                "elements": [{"type": "mrkdwn", "text": " | ".join(context_parts)}],
            }
        )

        blocks.append({"type": "divider"})

        return blocks

    def _format_news_item_blocks(self, item: NewsItem) -> list[dict]:
        """Format blocks for a single news item."""
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*<{item.url}|{item.title}>*",
                },
            },
        ]

        if item.summary:
            blocks.append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": item.summary[:200] + ("..." if len(item.summary) > 200 else ""),
                    },
                }
            )

        context_parts = [f"_{item.source}_"]
        if item.published_at:
            context_parts.append(item.published_at.strftime("%Y-%m-%d"))

        blocks.append(
            {
                "type": "context",
                "elements": [{"type": "mrkdwn", "text": " | ".join(context_parts)}],
            }
        )

        return blocks

    def _format_daily_digest_blocks(self, items: list[NewsItem]) -> list[dict]:
        """Format blocks for daily digest."""
        today = datetime.now().strftime("%A, %B %d, %Y")

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "📊 Daily Mortgage News Digest",
                    "emoji": True,
                },
            },
            {
                "type": "context",
                "elements": [{"type": "mrkdwn", "text": f"*{today}* | {len(items)} stories"}],
            },
            {"type": "divider"},
        ]

        # Group by importance: breaking news first, then by source
        breaking = [i for i in items if i.is_breaking_news]
        regular = [i for i in items if not i.is_breaking_news]

        # Add breaking news section if any
        if breaking:
            blocks.append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*🚨 Top Stories*",
                    },
                }
            )

            for item in breaking[:5]:
                blocks.extend(self._format_digest_item(item))

            blocks.append({"type": "divider"})

        # Add regular news
        if regular:
            blocks.append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*📰 More News*",
                    },
                }
            )

            for item in regular[:10]:
                blocks.extend(self._format_digest_item(item))

        # Footer
        blocks.append({"type": "divider"})
        blocks.append(
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"_Digest generated at {datetime.now().strftime('%H:%M')} | Powered by Mortgage News Monitor_",
                    }
                ],
            }
        )

        return blocks

    def _format_digest_item(self, item: NewsItem) -> list[dict]:
        """Format a single item for the digest."""
        text = f"• *<{item.url}|{item.title}>*"
        if item.source:
            text += f" _({item.source})_"

        return [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": text,
                },
            }
        ]
