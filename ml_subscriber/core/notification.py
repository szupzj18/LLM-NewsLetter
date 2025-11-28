import abc
import html
from typing import List

import requests

from .models import Article


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


class TelegramNotifier(Notifier):
    """
    A class to send notifications to a Telegram chat.
    """

    def __init__(self, bot_token: str, chat_id: str):
        """
        Initializes the TelegramNotifier.

        Args:
            bot_token: The token for the Telegram bot.
            chat_id: The ID of the chat to send messages to.
        """
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"

    def send(self, articles: List[Article]) -> None:
        """
        Sends a list of articles as a notification.

        Args:
            articles: A list of Article objects.
        """
        if not articles:
            self._send_no_article_reminder()
            return

        message = self._format_message(articles)
        self._send_message(message)

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
            authors_text = ', '.join(article.authors) if article.authors else "Unknown"
            authors = self._escape_html(authors_text)
            message += f'📄 <b><a href="{article.link}">{title}</a></b>\n'
            message += f"👤 <i>{authors}</i>\n\n"
        return message

    def _infer_source(self, articles: List[Article]) -> str:
        if not articles:
            return "unknown"
        return articles[0].metadata.get("source", "unknown")

    def _heading_for_source(self, source: str) -> str:
        if source == "hn":
            return "🚀 <b>Hacker News 热门讨论</b>"
        if source == "arxiv":
            return "✨ <b>New ML/DL Papers Found!</b> ✨"
        return "📢 <b>New Articles</b>"

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


class WebhookNotifier(Notifier):
    """
    A class to send notifications via a webhook.
    """

    def __init__(self, webhook_url: str):
        """
        Initializes the WebhookNotifier.

        Args:
            webhook_url: The webhook URL to send messages to.
        """
        self.webhook_url = webhook_url

    def send(self, articles: List[Article]) -> None:
        """
        Sends a list of articles as a notification.

        Args:
            articles: A list of Article objects.
        """
        if not articles:
            self._send_no_article_reminder()
            return

        message = self._format_message(articles)
        self._send_message(message)

    def _format_message(self, articles: List[Article]) -> dict:
        """
        Formats a list of articles into a single message string for Feishu.
        """
        source = self._infer_source(articles)
        heading = self._heading_for_source(source)
        text_content = f"{heading}\n\n"
        for article in articles:
            title = article.title
            authors_text = ', '.join(article.authors) if article.authors else "Unknown"
            text_content += f"📄 {title}\n🔗 {article.link}\n👤 {authors_text}\n\n"

        return {
            "msg_type": "text",
            "content": {
                "text": text_content
            }
        }

    def _infer_source(self, articles: List[Article]) -> str:
        if not articles:
            return "unknown"
        return articles[0].metadata.get("source", "unknown")

    def _heading_for_source(self, source: str) -> str:
        if source == "hn":
            return "🚀 Hacker News 热门讨论"
        if source == "arxiv":
            return "✨ New ML/DL Papers Found! ✨"
        return "📢 New Articles"

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
