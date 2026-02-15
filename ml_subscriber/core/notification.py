import abc
import html
from typing import Any, Dict, List, Optional

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


class TelegramNotifier(Notifier):
    """
    A class to send notifications to a Telegram chat.
    """

    def __init__(
        self,
        bot_token: str,
        chat_id: str,
        translator: Optional[Translator] = None,
        style: str = "detailed",
        message_format: str = "text",
    ):
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
        self.translator = translator or NoOpTranslator()
        self.style = style
        self.message_format = message_format

    def send(self, articles: List[Article]) -> None:
        """
        Sends a list of articles as a notification.

        Args:
            articles: A list of Article objects.
        """
        if not articles:
            self._send_no_article_reminder()
            return

        if self.message_format == "markdown":
            message = self._format_message_markdown_v2(articles)
            self._send_message(message, parse_mode="MarkdownV2")
            return

        message = self._format_message_html(articles)
        self._send_message(message, parse_mode="HTML")

    def _escape_html(self, text: str) -> str:
        """Escapes text for Telegram's HTML parser."""
        return html.escape(text)

    def _escape_markdown_v2(self, text: str) -> str:
        """
        Escapes text for Telegram MarkdownV2.
        Ref: https://core.telegram.org/bots/api#markdownv2-style
        """
        if text is None:
            return ""
        # Backslash must be escaped first.
        escaped = text.replace("\\", "\\\\")
        for ch in ["_", "*", "[", "]", "(", ")", "~", "`", ">", "#", "+", "-", "=", "|", "{", "}", ".", "!"]:
            escaped = escaped.replace(ch, f"\\{ch}")
        return escaped

    def _truncate_summary(self, summary: str, max_length: int = 300) -> str:
        """Truncates a summary to a maximum length."""
        if not summary or len(summary) <= max_length:
            return summary
        return summary[:max_length].rsplit(' ', 1)[0] + "..."

    def _format_message_html(self, articles: List[Article]) -> str:
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
            if self.style != "compact" and article.summary and not self._is_default_hn_summary(article):
                summary = self._truncate_summary(article.summary)
                summary_escaped = self._escape_html(summary)
                summary_zh = self._escape_html(self.translator.translate(summary))
                message += f"📝 {summary_escaped}\n"
                if summary_zh != summary_escaped:
                    message += f"📝 {summary_zh}\n"
            message += "\n"
        return message

    def _format_message_markdown_v2(self, articles: List[Article]) -> str:
        source = self._infer_source(articles)
        heading_plain = self._heading_for_source_plain(source)
        heading = f"*{self._escape_markdown_v2(heading_plain)}*"

        parts: List[str] = [heading, ""]
        for article in articles:
            title = self._escape_markdown_v2(article.title)
            link = self._escape_markdown_v2(article.link)
            parts.append(f"📄 [{title}]({link})")

            title_zh_raw = self.translator.translate(article.title)
            if title_zh_raw and title_zh_raw != article.title:
                parts.append(f"📄 *{self._escape_markdown_v2(title_zh_raw)}*")

            if self.style != "compact" and article.summary and not self._is_default_hn_summary(article):
                summary = self._truncate_summary(article.summary)
                parts.append(f"📝 {self._escape_markdown_v2(summary)}")

                summary_zh_raw = self.translator.translate(summary)
                if summary_zh_raw and summary_zh_raw != summary:
                    parts.append(f"📝 {self._escape_markdown_v2(summary_zh_raw)}")

            parts.append("")  # blank line between articles

        return "\n".join(parts).rstrip() + "\n"

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

    def _heading_for_source_plain(self, source: str) -> str:
        if source == "hn":
            return "🚀 Hacker News 热门讨论"
        if source == "arxiv":
            return "✨ New ML/DL Papers Found! ✨"
        return "📢 New Articles"

    def _is_default_hn_summary(self, article: Article) -> bool:
        """Check if article is a HN story with the default summary."""
        return (
            article.metadata.get("source") == "hn"
            and article.summary == "Hacker News story"
        )

    def _send_no_article_reminder(self):
        if self.message_format == "markdown":
            message = "*📭 No new articles this time\\.*\n"
            self._send_message(message, parse_mode="MarkdownV2")
            return

        message = "📭 <b>No new articles this time.</b>"
        self._send_message(message, parse_mode="HTML")

    def _send_message(self, message: str, parse_mode: str):
        """
        Sends a message to the Telegram chat.
        """
        payload = {
            'chat_id': self.chat_id,
            'text': message,
            'parse_mode': parse_mode
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
        style: str = "detailed",
        message_format: str = "text",
    ):
        """
        Initializes the WebhookNotifier.

        Args:
            webhook_url: The webhook URL to send messages to.
            translator: Optional translator for translating content.
        """
        if not self._is_feishu_webhook(webhook_url):
            raise ValueError(
                "Only Feishu/Lark webhook is supported. "
                "Expected URL containing '/open-apis/bot/v2/hook/'."
            )
        self.webhook_url = webhook_url
        self.translator = translator or NoOpTranslator()
        self.style = style
        self.message_format = message_format

    def send(self, articles: List[Article]) -> None:
        """
        Sends a list of articles as a notification.

        Args:
            articles: A list of Article objects.
        """
        if not articles:
            self._send_no_article_reminder()
            return

        payload = self._build_payload(articles)
        self._send_message(payload)

    def _truncate_summary(self, summary: str, max_length: int = 300) -> str:
        """Truncates a summary to a maximum length."""
        if not summary or len(summary) <= max_length:
            return summary
        return summary[:max_length].rsplit(' ', 1)[0] + "..."

    @staticmethod
    def _is_feishu_webhook(webhook_url: str) -> bool:
        url = (webhook_url or "").lower()
        return (
            "open.feishu.cn/open-apis/bot/v2/hook" in url
            or "open.larksuite.com/open-apis/bot/v2/hook" in url
        )

    def _format_text(self, articles: List[Article]) -> str:
        source = self._infer_source(articles)
        heading = self._heading_for_source(source)
        text_content = f"{heading}\n\n"

        for article in articles:
            title = article.title
            title_zh = self.translator.translate(article.title)
            text_content += f"📄 {title}\n"
            if title_zh and title_zh != title:
                text_content += f"📄 {title_zh}\n"
            text_content += f"🔗 {article.link}\n"
            if self.style != "compact" and article.summary and not self._is_default_hn_summary(article):
                summary = self._truncate_summary(article.summary)
                summary_zh = self.translator.translate(summary)
                text_content += f"📝 {summary}\n"
                if summary_zh and summary_zh != summary:
                    text_content += f"📝 {summary_zh}\n"
            text_content += "\n"

        return text_content

    def _build_payload(self, articles: List[Article]) -> Dict[str, Any]:
        if self.message_format == "markdown":
            # Feishu/Lark doesn't support raw Markdown; use "post" (rich text)
            # to provide Markdown-like rendering (links, paragraphs).
            return self._build_feishu_post_payload(articles)

        # Text mode (Feishu/Lark "text")
        text = self._format_text(articles)
        return {"msg_type": "text", "content": {"text": text}}

    def _build_feishu_post_payload(self, articles: List[Article]) -> Dict[str, Any]:
        """
        Build a Feishu/Lark "post" payload which supports rich text (links, basic emphasis).
        """
        source = self._infer_source(articles)
        title = self._heading_for_source(source)

        content: List[List[Dict[str, Any]]] = []
        # Heading as first paragraph
        content.append([{"tag": "text", "text": title}])

        for article in articles:
            # Title with link
            content.append([{"tag": "a", "text": f"📄 {article.title}", "href": article.link}])

            title_zh = self.translator.translate(article.title)
            if title_zh and title_zh != article.title:
                content.append([{"tag": "text", "text": f"📄 {title_zh}"}])

            if self.style != "compact" and article.summary and not self._is_default_hn_summary(article):
                summary = self._truncate_summary(article.summary)
                content.append([{"tag": "text", "text": f"📝 {summary}"}])
                summary_zh = self.translator.translate(summary)
                if summary_zh and summary_zh != summary:
                    content.append([{"tag": "text", "text": f"📝 {summary_zh}"}])

            # Blank line between items
            content.append([{"tag": "text", "text": ""}])

        return {
            "msg_type": "post",
            "content": {
                "post": {
                    "zh_cn": {
                        "title": title,
                        "content": content,
                    }
                }
            },
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

    def _is_default_hn_summary(self, article: Article) -> bool:
        """Check if article is a HN story with the default summary."""
        return (
            article.metadata.get("source") == "hn"
            and article.summary == "Hacker News story"
        )

    def _send_no_article_reminder(self):
        if self.message_format == "markdown":
            payload = {
                "msg_type": "post",
                "content": {
                    "post": {
                        "zh_cn": {
                            "title": "📭 No new articles this time.",
                            "content": [[{"tag": "text", "text": "📭 No new articles this time."}]],
                        }
                    }
                },
            }
            self._send_message(payload)
            return

        payload = {"msg_type": "text", "content": {"text": "📭 No new articles this time."}}
        self._send_message(payload)

    def _send_message(self, message: dict):
        """
        Sends a message to the webhook.
        """
        try:
            response = requests.post(self.webhook_url, json=message)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"Error sending message to webhook: {e}")
