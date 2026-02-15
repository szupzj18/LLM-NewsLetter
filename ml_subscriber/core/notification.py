import abc
import html
from typing import Any, List, Optional

import requests

from .models import Article
from .translator import Translator, NoOpTranslator


class Notifier(abc.ABC):
    """
    Abstract base class for notifiers.
    """

    @abc.abstractmethod
    def send(self, articles: List[Article]) -> None:
        """
        Sends a list of articles as a notification.
        Args:
            articles: A list of Article objects.
        """
        raise NotImplementedError


class ArticleNotifier(Notifier, abc.ABC):
    """Shared behavior for article-based notifiers."""

    HEADING_HN = "🚀 Hacker News 热门讨论"
    HEADING_ARXIV = "✨ New ML/DL Papers Found! ✨"
    HEADING_DEFAULT = "📢 New Articles"

    def __init__(self, translator: Optional[Translator] = None):
        self.translator = translator or NoOpTranslator()

    def send(self, articles: List[Article]) -> None:
        """Sends a list of articles as a notification."""
        if not articles:
            self._send_no_article_reminder()
            return

        message = self._format_message(articles)
        self._send_message(message)

    def _truncate_summary(self, summary: str, max_length: int = 300) -> str:
        """Truncates a summary to a maximum length."""
        if not summary or len(summary) <= max_length:
            return summary
        return summary[:max_length].rsplit(' ', 1)[0] + "..."

    def _infer_source(self, articles: List[Article]) -> str:
        if not articles:
            return "unknown"
        return articles[0].metadata.get("source", "unknown")

    def _heading_for_source(self, source: str) -> str:
        if source == "hn":
            return self.HEADING_HN
        if source == "arxiv":
            return self.HEADING_ARXIV
        return self.HEADING_DEFAULT

    def _is_default_hn_summary(self, article: Article) -> bool:
        """Check if article is a HN story with the default summary."""
        return (
            article.metadata.get("source") == "hn"
            and article.summary == "Hacker News story"
        )

    @abc.abstractmethod
    def _format_message(self, articles: List[Article]) -> Any:
        """Formats articles into a notifier-specific payload."""
        raise NotImplementedError

    @abc.abstractmethod
    def _send_no_article_reminder(self):
        """Sends a reminder payload when there are no new articles."""
        raise NotImplementedError

    @abc.abstractmethod
    def _send_message(self, message: Any):
        """Sends a notifier-specific payload."""
        raise NotImplementedError


class TelegramNotifier(ArticleNotifier):
    """
    A class to send notifications to a Telegram chat.
    """

    HEADING_HN = "🚀 <b>Hacker News 热门讨论</b>"
    HEADING_ARXIV = "✨ <b>New ML/DL Papers Found!</b> ✨"
    HEADING_DEFAULT = "📢 <b>New Articles</b>"

    def __init__(self, bot_token: str, chat_id: str, translator: Optional[Translator] = None):
        """
        Initializes the TelegramNotifier.

        Args:
            bot_token: The token for the Telegram bot.
            chat_id: The ID of the chat to send messages to.
            translator: Optional translator for translating content.
        """
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        super().__init__(translator=translator)

    def _escape_html(self, text: str) -> str:
        """Escapes text for Telegram's HTML parser."""
        return html.escape(text)

    def _format_message(self, articles: List[Article]) -> str:
        """
        Formats a list of articles into a single HTML message string.
        """
        source = self._infer_source(articles)
        heading = self._heading_for_source(source)
        message = f"{heading}\n\n"
        for article in articles:
            title = self._escape_html(article.title)
            title_zh = self._escape_html(self.translator.translate(article.title))
            message += f'📄 <b><a href="{article.link}">{title}</a></b>\n'
            if title_zh != title:
                message += f"📄 <b>{title_zh}</b>\n"
            if article.summary and not self._is_default_hn_summary(article):
                summary = self._truncate_summary(article.summary)
                summary_escaped = self._escape_html(summary)
                summary_zh = self._escape_html(self.translator.translate(summary))
                message += f"📝 {summary_escaped}\n"
                if summary_zh != summary_escaped:
                    message += f"📝 {summary_zh}\n"
            message += "\n"
        return message

    def _send_no_article_reminder(self):
        message = "📭 <b>No new articles this time.</b>"
        self._send_message(message)

    def _send_message(self, message: str):
        """
        Sends a message to the Telegram chat.
        """
        payload = {
            'chat_id': self.chat_id,
            'text': message,
            'parse_mode': 'HTML'
        }
        try:
            response = requests.post(self.api_url, json=payload)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"Error sending message to Telegram: {e}")


class WebhookNotifier(ArticleNotifier):
    """
    A class to send notifications via a webhook.
    """

    def __init__(self, webhook_url: str, translator: Optional[Translator] = None):
        """
        Initializes the WebhookNotifier.

        Args:
            webhook_url: The webhook URL to send messages to.
            translator: Optional translator for translating content.
        """
        self.webhook_url = webhook_url
        super().__init__(translator=translator)

    def _format_message(self, articles: List[Article]) -> dict:
        """
        Formats a list of articles into a single message string for Feishu.
        """
        source = self._infer_source(articles)
        heading = self._heading_for_source(source)
        text_content = f"{heading}\n\n"
        for article in articles:
            title = article.title
            title_zh = self.translator.translate(article.title)
            text_content += f"📄 {title}\n"
            if title_zh != title:
                text_content += f"📄 {title_zh}\n"
            text_content += f"🔗 {article.link}\n"
            if article.summary and not self._is_default_hn_summary(article):
                summary = self._truncate_summary(article.summary)
                summary_zh = self.translator.translate(summary)
                text_content += f"📝 {summary}\n"
                if summary_zh != summary:
                    text_content += f"📝 {summary_zh}\n"
            text_content += "\n"

        return {
            "msg_type": "text",
            "content": {
                "text": text_content
            }
        }

    def _send_no_article_reminder(self):
        message = {
            "msg_type": "text",
            "content": {
                "text": "📭 No new articles this time."
            }
        }
        self._send_message(message)

    def _send_message(self, message: dict):
        """
        Sends a message to the webhook.
        """
        try:
            response = requests.post(self.webhook_url, json=message)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"Error sending message to webhook: {e}")
