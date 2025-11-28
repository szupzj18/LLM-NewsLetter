import abc
import html
from typing import List, Optional

import requests

from .models import Article
from .translator import Translator, NoOpTranslator


STYLE_DETAILED = "detailed"
STYLE_COMPACT = "compact"
FORMAT_TEXT = "text"
FORMAT_MARKDOWN = "markdown"
MD_SPECIALS = "_*[]()~`>#+-=|{}.!\\"


def truncate_summary(summary: str, max_length: int = 300) -> str:
    """Truncate long summaries to keep notification concise."""
    if not summary or len(summary) <= max_length:
        return summary
    return summary[:max_length].rsplit(' ', 1)[0] + "..."


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

    def __init__(
        self,
        bot_token: str,
        chat_id: str,
        translator: Optional[Translator] = None,
        style: str = STYLE_DETAILED,
        message_format: str = FORMAT_TEXT,
    ):
        """
        Initializes the TelegramNotifier.

        Args:
            bot_token: The token for the Telegram bot.
            chat_id: The ID of the chat to send messages to.
            translator: Optional translator for translating content.
            style: Controls whether notifications are 'detailed' or 'compact'.
            message_format: 'text' (HTML) or 'markdown'.
        """
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        self.translator = translator or NoOpTranslator()
        self.style = style if style in {STYLE_DETAILED, STYLE_COMPACT} else STYLE_DETAILED
        self.message_format = (
            message_format if message_format in {FORMAT_TEXT, FORMAT_MARKDOWN} else FORMAT_TEXT
        )
        self.parse_mode = "MarkdownV2" if self.message_format == FORMAT_MARKDOWN else "HTML"

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

    def _format_message(self, articles: List[Article]) -> str:
        """Format articles based on the desired output format."""
        if self.message_format == FORMAT_MARKDOWN:
            return self._format_markdown(articles)
        return self._format_html(articles)

    def _format_html(self, articles: List[Article]) -> str:
        source = self._infer_source(articles)
        heading = self._heading_for_source_html(source)
        message = f"{heading}\n\n"
        include_summary = self.style == STYLE_DETAILED
        for article in articles:
            message += self._format_article_html(article, include_summary)
        return message

    def _format_article_html(self, article: Article, include_summary: bool) -> str:
        link = html.escape(article.link, quote=True)
        title = self._escape_html(article.title)
        translated_title = self._escape_html(self.translator.translate(article.title))

        block = f'📄 <b><a href="{link}">{title}</a></b>\n'
        if translated_title != title:
            block += f"📄 <b>{translated_title}</b>\n"

        if include_summary and article.summary:
            summary = truncate_summary(article.summary)
            summary_escaped = self._escape_html(summary)
            summary_translated = self._escape_html(self.translator.translate(summary))
            block += f"📝 {summary_escaped}\n"
            if summary_translated != summary_escaped:
                block += f"📝 {summary_translated}\n"

        block += "\n"
        return block

    def _format_markdown(self, articles: List[Article]) -> str:
        source = self._infer_source(articles)
        heading = self._heading_for_source_markdown(source)
        message = f"{heading}\n\n"
        include_summary = self.style == STYLE_DETAILED
        for article in articles:
            message += self._format_article_markdown(article, include_summary)
        return message

    def _format_article_markdown(self, article: Article, include_summary: bool) -> str:
        link = self._escape_markdown_link(article.link)
        title = self._escape_markdown(article.title)
        translated_title = self._escape_markdown(self.translator.translate(article.title))

        block = f"📄 [{title}]({link})\n"
        if translated_title != title:
            block += f"📄 {translated_title}\n"

        if include_summary and article.summary:
            summary = truncate_summary(article.summary)
            summary_md = self._escape_markdown(summary)
            block += f"📝 {summary_md}\n"

            summary_translated = self._escape_markdown(self.translator.translate(summary))
            if summary_translated != summary_md:
                block += f"📝 {summary_translated}\n"

        block += "\n"
        return block

    def _escape_html(self, text: str) -> str:
        """Escapes text for Telegram's HTML parser."""
        return html.escape(text)

    def _escape_markdown(self, text: str) -> str:
        if not text:
            return text
        return "".join(f"\\{char}" if char in MD_SPECIALS else char for char in text)

    def _escape_markdown_link(self, url: str) -> str:
        if not url:
            return url
        return url.replace("(", "\\(").replace(")", "\\)")

    def _infer_source(self, articles: List[Article]) -> str:
        if not articles:
            return "unknown"
        return articles[0].metadata.get("source", "unknown")

    def _heading_for_source_html(self, source: str) -> str:
        if source == "hn":
            return "🚀 <b>Hacker News 热门讨论</b>"
        if source == "arxiv":
            return "✨ <b>New ML/DL Papers Found!</b> ✨"
        return "📢 <b>New Articles</b>"

    def _heading_for_source_markdown(self, source: str) -> str:
        if source == "hn":
            return "🚀 *Hacker News 热门讨论*"
        if source == "arxiv":
            return "✨ *New ML/DL Papers Found!* ✨"
        return "📢 *New Articles*"

    def _send_no_article_reminder(self):
        if self.message_format == FORMAT_MARKDOWN:
            message = self._escape_markdown("📭 No new articles this time.")
        else:
            message = "📭 <b>No new articles this time.</b>"
        self._send_message(message)

    def _send_message(self, message: str):
        """
        Sends a message to the Telegram chat.
        """
        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": self.parse_mode,
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

    def __init__(
        self,
        webhook_url: str,
        translator: Optional[Translator] = None,
        style: str = STYLE_DETAILED,
        message_format: str = FORMAT_TEXT,
    ):
        """
        Initializes the WebhookNotifier.

        Args:
            webhook_url: The webhook URL to send messages to.
            translator: Optional translator for translating content.
            style: Controls whether notifications are 'detailed' or 'compact'.
            message_format: 'text' payloads or Markdown content.
        """
        self.webhook_url = webhook_url
        self.translator = translator or NoOpTranslator()
        self.style = style if style in {STYLE_DETAILED, STYLE_COMPACT} else STYLE_DETAILED
        self.message_format = (
            message_format if message_format in {FORMAT_TEXT, FORMAT_MARKDOWN} else FORMAT_TEXT
        )

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
        source = self._infer_source(articles)
        include_summary = self.style == STYLE_DETAILED

        if self.message_format == FORMAT_MARKDOWN:
            content = self._format_markdown(articles, source, include_summary)
            return {
                "msg_type": "markdown",
                "content": {
                    "text": content,
                },
            }

        content = self._format_text(articles, source, include_summary)
        return {
            "msg_type": "text",
            "content": {
                "text": content,
            },
        }

    def _format_text(self, articles: List[Article], source: str, include_summary: bool) -> str:
        heading = self._heading_for_source_text(source)
        text_content = f"{heading}\n\n"
        for article in articles:
            text_content += self._format_article_text(article, include_summary)
        return text_content

    def _format_article_text(self, article: Article, include_summary: bool) -> str:
        title = article.title
        translated_title = self.translator.translate(article.title)
        block = f"📄 {title}\n"
        if translated_title != title:
            block += f"📄 {translated_title}\n"
        block += f"🔗 {article.link}\n"

        if include_summary and article.summary:
            summary = truncate_summary(article.summary)
            block += f"📝 {summary}\n"
            summary_translated = self.translator.translate(summary)
            if summary_translated != summary:
                block += f"📝 {summary_translated}\n"

        block += "\n"
        return block

    def _format_markdown(
        self,
        articles: List[Article],
        source: str,
        include_summary: bool,
    ) -> str:
        heading = self._heading_for_source_markdown(source)
        text_content = f"{heading}\n\n"
        for article in articles:
            text_content += self._format_article_markdown(article, include_summary)
        return text_content

    def _format_article_markdown(self, article: Article, include_summary: bool) -> str:
        block = f"📄 [{article.title}]({article.link})\n"
        translated_title = self.translator.translate(article.title)
        if translated_title != article.title:
            block += f"📄 {translated_title}\n"

        if include_summary and article.summary:
            summary = truncate_summary(article.summary)
            block += f"📝 {summary}\n"
            summary_translated = self.translator.translate(summary)
            if summary_translated != summary:
                block += f"📝 {summary_translated}\n"

        block += "\n"
        return block

    def _infer_source(self, articles: List[Article]) -> str:
        if not articles:
            return "unknown"
        return articles[0].metadata.get("source", "unknown")

    def _heading_for_source_text(self, source: str) -> str:
        if source == "hn":
            return "🚀 Hacker News 热门讨论"
        if source == "arxiv":
            return "✨ New ML/DL Papers Found! ✨"
        return "📢 New Articles"

    def _heading_for_source_markdown(self, source: str) -> str:
        if source == "hn":
            return "**🚀 Hacker News 热门讨论**"
        if source == "arxiv":
            return "**✨ New ML/DL Papers Found! ✨**"
        return "**📢 New Articles**"

    def _send_no_article_reminder(self):
        if self.message_format == FORMAT_MARKDOWN:
            message = {
                "msg_type": "markdown",
                "content": {
                    "text": "📭 _No new articles this time._",
                },
            }
        else:
            message = {
                "msg_type": "text",
                "content": {
                    "text": "📭 No new articles this time.",
                },
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
