import unittest
from unittest.mock import patch, MagicMock
import argparse
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import (
    get_fetcher_for_source,
    get_webhook_url,
    get_configured_notifiers,
    resolve_notifiers,
    ensure_dir,
    create_notifier,
    send_notification,
    broadcast_notifications,
)
from ml_subscriber.core.arxiv_fetcher import ArxivFetcher
from ml_subscriber.core.hn_fetcher import HackerNewsFetcher
from ml_subscriber.core.notification import TelegramNotifier, WebhookNotifier
from ml_subscriber.core.models import Article


class TestGetFetcherForSource(unittest.TestCase):
    """测试 get_fetcher_for_source 函数"""

    def test_returns_arxiv_fetcher_by_default(self):
        fetcher = get_fetcher_for_source("arxiv")
        self.assertIsInstance(fetcher, ArxivFetcher)

    def test_returns_hn_fetcher_for_hn_source(self):
        fetcher = get_fetcher_for_source("hn")
        self.assertIsInstance(fetcher, HackerNewsFetcher)

    def test_returns_arxiv_fetcher_for_unknown_source(self):
        fetcher = get_fetcher_for_source("unknown")
        self.assertIsInstance(fetcher, ArxivFetcher)


class TestGetWebhookUrl(unittest.TestCase):
    """测试 get_webhook_url 函数"""

    def test_returns_args_webhook_url_if_provided(self):
        args = argparse.Namespace(webhook_url="http://args-webhook.com")
        result = get_webhook_url(args)
        self.assertEqual(result, "http://args-webhook.com")

    @patch.dict(os.environ, {"WEBHOOK_URL": "http://env-webhook.com"})
    def test_returns_env_webhook_url_if_args_not_provided(self):
        args = argparse.Namespace(webhook_url=None)
        result = get_webhook_url(args)
        self.assertEqual(result, "http://env-webhook.com")

    @patch.dict(os.environ, {"WEBHOOK_URL": "http://env-webhook.com"})
    def test_args_takes_precedence_over_env(self):
        args = argparse.Namespace(webhook_url="http://args-webhook.com")
        result = get_webhook_url(args)
        self.assertEqual(result, "http://args-webhook.com")

    @patch.dict(os.environ, {}, clear=True)
    def test_returns_none_if_nothing_configured(self):
        args = argparse.Namespace(webhook_url=None)
        result = get_webhook_url(args)
        self.assertIsNone(result)


class TestGetConfiguredNotifiers(unittest.TestCase):
    """测试 get_configured_notifiers 函数"""

    @patch.dict(os.environ, {}, clear=True)
    def test_returns_empty_list_when_nothing_configured(self):
        result = get_configured_notifiers(None)
        self.assertEqual(result, [])

    @patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "token", "TELEGRAM_CHAT_ID": "chat"})
    def test_returns_telegram_when_configured(self):
        result = get_configured_notifiers(None)
        self.assertEqual(result, ["telegram"])

    @patch.dict(os.environ, {}, clear=True)
    def test_returns_webhook_when_url_provided(self):
        result = get_configured_notifiers("http://webhook.com")
        self.assertEqual(result, ["webhook"])

    @patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "token", "TELEGRAM_CHAT_ID": "chat"})
    def test_returns_both_when_both_configured(self):
        result = get_configured_notifiers("http://webhook.com")
        self.assertEqual(result, ["telegram", "webhook"])

    @patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "token"})  # 缺少 CHAT_ID
    def test_telegram_requires_both_token_and_chat_id(self):
        result = get_configured_notifiers(None)
        self.assertEqual(result, [])


class TestResolveNotifiers(unittest.TestCase):
    """测试 resolve_notifiers 函数"""

    def test_returns_empty_list_when_notifier_arg_is_none(self):
        result = resolve_notifiers(None, "http://webhook.com")
        self.assertEqual(result, [])

    def test_returns_single_notifier_for_telegram(self):
        result = resolve_notifiers("telegram", None)
        self.assertEqual(result, ["telegram"])

    def test_returns_single_notifier_for_webhook(self):
        result = resolve_notifiers("webhook", "http://webhook.com")
        self.assertEqual(result, ["webhook"])

    @patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "token", "TELEGRAM_CHAT_ID": "chat"})
    def test_returns_all_configured_notifiers_for_all(self):
        result = resolve_notifiers("all", "http://webhook.com")
        self.assertEqual(result, ["telegram", "webhook"])

    @patch.dict(os.environ, {}, clear=True)
    def test_returns_empty_list_for_all_when_nothing_configured(self):
        result = resolve_notifiers("all", None)
        self.assertEqual(result, [])


class TestEnsureDir(unittest.TestCase):
    """测试 ensure_dir 函数"""

    @patch('os.makedirs')
    def test_creates_directory_for_file_path(self, mock_makedirs):
        ensure_dir("/path/to/file.json")
        mock_makedirs.assert_called_once_with("/path/to", exist_ok=True)

    @patch('os.makedirs')
    def test_does_not_create_directory_for_filename_only(self, mock_makedirs):
        ensure_dir("file.json")
        mock_makedirs.assert_not_called()


class TestCreateNotifier(unittest.TestCase):
    """测试 create_notifier 函数"""

    @patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "token", "TELEGRAM_CHAT_ID": "chat"})
    def test_creates_telegram_notifier(self):
        notifier = create_notifier("telegram", None)
        self.assertIsInstance(notifier, TelegramNotifier)

    @patch.dict(os.environ, {}, clear=True)
    def test_returns_none_for_telegram_without_credentials(self):
        notifier = create_notifier("telegram", None)
        self.assertIsNone(notifier)

    def test_creates_webhook_notifier(self):
        notifier = create_notifier("webhook", "http://webhook.com")
        self.assertIsInstance(notifier, WebhookNotifier)

    def test_returns_none_for_webhook_without_url(self):
        notifier = create_notifier("webhook", None)
        self.assertIsNone(notifier)

    def test_returns_none_for_unknown_type(self):
        notifier = create_notifier("unknown", None)
        self.assertIsNone(notifier)


class TestSendNotification(unittest.TestCase):
    """测试 send_notification 函数"""

    @patch('main.create_notifier')
    def test_sends_notification_with_articles(self, mock_create_notifier):
        mock_notifier = MagicMock()
        mock_create_notifier.return_value = mock_notifier
        
        articles = [
            Article(
                title="Test",
                authors=["Author"],
                summary="Summary",
                link="http://test.com",
                published_date="2023-01-01",
                pdf_link="",
                metadata={}
            )
        ]
        
        send_notification(articles, "telegram", None)
        
        mock_notifier.send.assert_called_once_with(articles)

    @patch('main.create_notifier')
    def test_does_not_send_when_notifier_creation_fails(self, mock_create_notifier):
        mock_create_notifier.return_value = None
        
        # Should not raise an exception
        send_notification([], "telegram", None)


class TestBroadcastNotifications(unittest.TestCase):
    """测试 broadcast_notifications 函数"""

    @patch('main.send_notification')
    def test_sends_to_all_notifier_types(self, mock_send):
        articles = []
        notifier_types = ["telegram", "webhook"]
        webhook_url = "http://webhook.com"
        
        broadcast_notifications(articles, notifier_types, webhook_url)
        
        self.assertEqual(mock_send.call_count, 2)
        mock_send.assert_any_call(articles, "telegram", webhook_url)
        mock_send.assert_any_call(articles, "webhook", webhook_url)

    @patch('main.send_notification')
    def test_does_not_send_when_notifier_types_empty(self, mock_send):
        broadcast_notifications([], [], None)
        mock_send.assert_not_called()


if __name__ == '__main__':
    unittest.main()
