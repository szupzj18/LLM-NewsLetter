import unittest
from unittest.mock import patch, MagicMock, call
import argparse
import sys
import os

# Add project root to path
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
    handle_fetch,
    handle_notify,
    handle_visualize,
    main,
    parse_args,
)
from ml_subscriber.core.arxiv_fetcher import ArxivFetcher
from ml_subscriber.core.hn_fetcher import HackerNewsFetcher
from ml_subscriber.core.notification import TelegramNotifier, WebhookNotifier
from ml_subscriber.core.models import Article


def create_test_article(title="Test", link="http://test.com"):
    """Helper to create a test article."""
    return Article(
        title=title,
        authors=["Author"],
        summary="Summary",
        link=link,
        published_date="2023-01-01",
        pdf_link="",
        metadata={"source": "arxiv"}
    )


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


class TestHandleFetch(unittest.TestCase):
    """Test handle_fetch function."""

    def setUp(self):
        self.args = argparse.Namespace(
            source="arxiv",
            json_output="output/test.json",
            notifier="webhook",
            notify=False
        )

    @patch('main.broadcast_notifications')
    @patch('main.JsonStorage')
    @patch('main.ensure_dir')
    @patch('main.get_fetcher_for_source')
    def test_fetch_saves_articles(self, mock_get_fetcher, mock_ensure_dir, 
                                   mock_storage_class, mock_broadcast):
        """Test that fetched articles are saved."""
        mock_fetcher = MagicMock()
        mock_fetcher.fetch_articles.return_value = [create_test_article()]
        mock_get_fetcher.return_value = mock_fetcher
        
        mock_storage = MagicMock()
        mock_storage.load_articles.return_value = []
        mock_storage_class.return_value = mock_storage

        handle_fetch(self.args, "http://webhook.com")

        mock_storage.save_articles.assert_called_once()
        mock_ensure_dir.assert_called_once_with("output/test.json")

    @patch('main.broadcast_notifications')
    @patch('main.JsonStorage')
    @patch('main.ensure_dir')
    @patch('main.get_fetcher_for_source')
    def test_fetch_sends_notification_when_not_skipped(self, mock_get_fetcher, 
                                                        mock_ensure_dir,
                                                        mock_storage_class, 
                                                        mock_broadcast):
        """Test that notifications are sent when skip_notify=False."""
        mock_fetcher = MagicMock()
        articles = [create_test_article()]
        mock_fetcher.fetch_articles.return_value = articles
        mock_get_fetcher.return_value = mock_fetcher
        
        mock_storage = MagicMock()
        mock_storage.load_articles.return_value = []
        mock_storage_class.return_value = mock_storage

        handle_fetch(self.args, "http://webhook.com", skip_notify=False)

        mock_broadcast.assert_called_once()

    @patch('main.broadcast_notifications')
    @patch('main.JsonStorage')
    @patch('main.ensure_dir')
    @patch('main.get_fetcher_for_source')
    def test_fetch_skips_notification_when_skip_notify_true(self, mock_get_fetcher,
                                                             mock_ensure_dir,
                                                             mock_storage_class,
                                                             mock_broadcast):
        """Test that notifications are skipped when skip_notify=True."""
        mock_fetcher = MagicMock()
        mock_fetcher.fetch_articles.return_value = [create_test_article()]
        mock_get_fetcher.return_value = mock_fetcher
        
        mock_storage = MagicMock()
        mock_storage.load_articles.return_value = []
        mock_storage_class.return_value = mock_storage

        handle_fetch(self.args, "http://webhook.com", skip_notify=True)

        # Notifications should NOT be sent
        mock_broadcast.assert_not_called()

    @patch('main.broadcast_notifications')
    @patch('main.get_fetcher_for_source')
    def test_fetch_handles_no_articles(self, mock_get_fetcher, mock_broadcast):
        """Test behavior when no articles are fetched."""
        mock_fetcher = MagicMock()
        mock_fetcher.fetch_articles.return_value = []
        mock_get_fetcher.return_value = mock_fetcher

        handle_fetch(self.args, "http://webhook.com", skip_notify=False)

        # Should still send reminder notification
        mock_broadcast.assert_called_once_with([], ["webhook"], "http://webhook.com")

    @patch('main.broadcast_notifications')
    @patch('main.get_fetcher_for_source')
    def test_fetch_no_articles_skip_notify(self, mock_get_fetcher, mock_broadcast):
        """Test that no notification is sent when no articles and skip_notify=True."""
        mock_fetcher = MagicMock()
        mock_fetcher.fetch_articles.return_value = []
        mock_get_fetcher.return_value = mock_fetcher

        handle_fetch(self.args, "http://webhook.com", skip_notify=True)

        mock_broadcast.assert_not_called()

    @patch('main.broadcast_notifications')
    @patch('main.JsonStorage')
    @patch('main.ensure_dir')
    @patch('main.get_fetcher_for_source')
    def test_fetch_only_notifies_new_articles(self, mock_get_fetcher, mock_ensure_dir,
                                               mock_storage_class, mock_broadcast):
        """Test that only new articles are included in notification."""
        mock_fetcher = MagicMock()
        new_article = create_test_article(title="New", link="http://new.com")
        existing_article = create_test_article(title="Existing", link="http://existing.com")
        mock_fetcher.fetch_articles.return_value = [new_article, existing_article]
        mock_get_fetcher.return_value = mock_fetcher
        
        mock_storage = MagicMock()
        # Simulate existing_article already stored
        mock_storage.load_articles.return_value = [existing_article]
        mock_storage_class.return_value = mock_storage

        handle_fetch(self.args, "http://webhook.com", skip_notify=False)

        # Only new_article should be in notification
        call_args = mock_broadcast.call_args[0]
        notified_articles = call_args[0]
        self.assertEqual(len(notified_articles), 1)
        self.assertEqual(notified_articles[0].link, "http://new.com")


class TestHandleNotify(unittest.TestCase):
    """Test handle_notify function."""

    def setUp(self):
        self.args = argparse.Namespace(
            json_output="output/test.json",
            notifier="webhook"
        )

    @patch('main.broadcast_notifications')
    @patch('main.JsonStorage')
    def test_notify_sends_stored_articles(self, mock_storage_class, mock_broadcast):
        """Test that stored articles are sent."""
        mock_storage = MagicMock()
        articles = [create_test_article()]
        mock_storage.load_articles.return_value = articles
        mock_storage_class.return_value = mock_storage

        handle_notify(self.args, "http://webhook.com")

        mock_broadcast.assert_called_once_with(articles, ["webhook"], "http://webhook.com")

    @patch('main.broadcast_notifications')
    @patch('main.JsonStorage')
    def test_notify_no_articles_found(self, mock_storage_class, mock_broadcast):
        """Test behavior when no articles are stored."""
        mock_storage = MagicMock()
        mock_storage.load_articles.return_value = []
        mock_storage_class.return_value = mock_storage

        handle_notify(self.args, "http://webhook.com")

        mock_broadcast.assert_not_called()

    @patch('main.broadcast_notifications')
    def test_notify_requires_notifier_arg(self, mock_broadcast):
        """Test that --notifier is required."""
        args = argparse.Namespace(
            json_output="output/test.json",
            notifier=None
        )

        handle_notify(args, "http://webhook.com")

        mock_broadcast.assert_not_called()


class TestHandleVisualize(unittest.TestCase):
    """Test handle_visualize function."""

    def setUp(self):
        self.args = argparse.Namespace(
            json_output="output/test.json",
            output="output/test.html"
        )

    @patch('main.ArticleVisualizer')
    @patch('main.ensure_dir')
    @patch('main.JsonStorage')
    def test_visualize_generates_html(self, mock_storage_class, mock_ensure_dir,
                                       mock_visualizer_class):
        """Test that HTML is generated from stored articles."""
        mock_storage = MagicMock()
        articles = [create_test_article()]
        mock_storage.load_articles.return_value = articles
        mock_storage_class.return_value = mock_storage
        
        mock_visualizer = MagicMock()
        mock_visualizer_class.return_value = mock_visualizer

        handle_visualize(self.args)

        mock_ensure_dir.assert_called_once_with("output/test.html")
        mock_visualizer.generate_html.assert_called_once_with(articles, "output/test.html")

    @patch('main.ArticleVisualizer')
    @patch('main.JsonStorage')
    def test_visualize_no_articles(self, mock_storage_class, mock_visualizer_class):
        """Test behavior when no articles are stored."""
        mock_storage = MagicMock()
        mock_storage.load_articles.return_value = []
        mock_storage_class.return_value = mock_storage

        handle_visualize(self.args)

        mock_visualizer_class.assert_not_called()


class TestParseArgs(unittest.TestCase):
    """Test parse_args function."""

    def test_parse_fetch_flag(self):
        parser = parse_args()
        args = parser.parse_args(['--fetch'])
        self.assertTrue(args.fetch)

    def test_parse_notify_flag(self):
        parser = parse_args()
        args = parser.parse_args(['--notify'])
        self.assertTrue(args.notify)

    def test_parse_visualize_flag(self):
        parser = parse_args()
        args = parser.parse_args(['--visualize'])
        self.assertTrue(args.visualize)

    def test_parse_notifier_choices(self):
        parser = parse_args()
        for choice in ['telegram', 'webhook', 'all']:
            args = parser.parse_args(['--fetch', '--notifier', choice])
            self.assertEqual(args.notifier, choice)

    def test_parse_source_choices(self):
        parser = parse_args()
        for choice in ['arxiv', 'hn']:
            args = parser.parse_args(['--fetch', '--source', choice])
            self.assertEqual(args.source, choice)

    def test_default_values(self):
        parser = parse_args()
        args = parser.parse_args(['--fetch'])
        self.assertEqual(args.source, 'arxiv')
        self.assertEqual(args.output, 'output/articles.html')
        self.assertEqual(args.json_output, 'output/articles.json')


class TestMainFunction(unittest.TestCase):
    """Test main function integration."""

    @patch('main.handle_notify')
    @patch('main.handle_fetch')
    @patch('sys.argv', ['main.py', '--fetch', '--notify', '--notifier', 'webhook'])
    def test_main_fetch_and_notify_no_duplicate(self, mock_fetch, mock_notify):
        """Test that --fetch --notify doesn't cause duplicate notifications."""
        main()

        # handle_fetch should be called with skip_notify=True
        mock_fetch.assert_called_once()
        # Check that skip_notify keyword argument is True
        _, kwargs = mock_fetch.call_args
        self.assertTrue(kwargs.get('skip_notify', False))
        
        # handle_notify should also be called
        mock_notify.assert_called_once()

    @patch('main.handle_notify')
    @patch('main.handle_fetch')
    @patch('sys.argv', ['main.py', '--fetch', '--notifier', 'webhook'])
    def test_main_fetch_only_sends_notification(self, mock_fetch, mock_notify):
        """Test that --fetch alone sends notification."""
        main()

        # handle_fetch should be called with skip_notify=False (args.notify is False)
        mock_fetch.assert_called_once()
        _, kwargs = mock_fetch.call_args
        self.assertFalse(kwargs.get('skip_notify', True))
        mock_notify.assert_not_called()

    @patch('main.handle_visualize')
    @patch('sys.argv', ['main.py', '--visualize'])
    def test_main_visualize_only(self, mock_visualize):
        """Test --visualize command."""
        main()
        mock_visualize.assert_called_once()

    @patch('builtins.print')
    @patch('sys.argv', ['main.py'])
    def test_main_no_args_prints_help(self, mock_print):
        """Test that no arguments prints help."""
        # This will call parser.print_help() which we can't easily mock,
        # but we can verify main doesn't crash
        main()


if __name__ == '__main__':
    unittest.main()
