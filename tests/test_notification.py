import unittest
from unittest.mock import patch, MagicMock
from ml_subscriber.core.notification import TelegramNotifier, WebhookNotifier
from ml_subscriber.core.models import Article
from ml_subscriber.core.translator import Translator


def create_article(
    title="Test Title",
    summary="Test Summary",
    link="http://test.com",
    source="arxiv",
    author="Test Author",
    pdf_link="http://test.com/test.pdf",
):
    """Build a test article with sensible defaults."""
    return Article(
        title=title,
        authors=[author],
        summary=summary,
        link=link,
        published_date="2023-10-27T10:00:00Z",
        pdf_link=pdf_link,
        metadata={"source": source},
    )


def setup_successful_post(mock_post):
    """Configure requests.post mock with a successful response."""
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response


class TestTelegramNotifier(unittest.TestCase):

    def setUp(self):
        self.bot_token = "test_token"
        self.chat_id = "test_chat_id"
        self.notifier = TelegramNotifier(self.bot_token, self.chat_id)

    def _assert_sent_text(self, mock_post, expected_text):
        expected_payload = {
            'chat_id': self.chat_id,
            'text': expected_text,
            'parse_mode': 'HTML'
        }
        mock_post.assert_called_once_with(
            f"https://api.telegram.org/bot{self.bot_token}/sendMessage",
            json=expected_payload
        )

    @patch('requests.post')
    def test_send_success_by_source(self, mock_post):
        """Test Telegram heading and formatting for each supported source."""
        cases = [
            (
                "arxiv",
                create_article(),
                "✨ <b>New ML/DL Papers Found!</b> ✨\n\n"
                "📄 <b><a href=\"http://test.com\">Test Title</a></b>\n"
                "📝 Test Summary\n\n",
            ),
            (
                "hn",
                create_article(
                    title="HN Title",
                    summary="HN Summary",
                    link="http://hn.com/story",
                    source="hn",
                    author="HN Author",
                    pdf_link="",
                ),
                "🚀 <b>Hacker News 热门讨论</b>\n\n"
                "📄 <b><a href=\"http://hn.com/story\">HN Title</a></b>\n"
                "📝 HN Summary\n\n",
            ),
        ]

        for source, article, expected_message in cases:
            with self.subTest(source=source):
                mock_post.reset_mock()
                setup_successful_post(mock_post)
                self.notifier.send([article])
                self._assert_sent_text(mock_post, expected_message)

    @patch('requests.post')
    def test_send_no_articles(self, mock_post):
        """Test that send method sends a reminder when no articles are provided."""
        setup_successful_post(mock_post)

        self.notifier.send([])

        self._assert_sent_text(mock_post, "📭 <b>No new articles this time.</b>")

class TestWebhookNotifier(unittest.TestCase):

    def setUp(self):
        self.webhook_url = "https://open.feishu.cn/open-apis/bot/v2/hook/test-webhook"
        self.notifier = WebhookNotifier(self.webhook_url)

    def test_accepts_larkoffice_webhook_url(self):
        notifier = WebhookNotifier(
            "https://open.larkoffice.com/open-apis/bot/v2/hook/test-webhook"
        )
        self.assertIsInstance(notifier, WebhookNotifier)

    def _assert_sent_text(self, mock_post, expected_text):
        expected_payload = {
            "msg_type": "text",
            "content": {
                "text": expected_text
            }
        }
        mock_post.assert_called_once_with(self.webhook_url, json=expected_payload)

    @patch('requests.post')
    def test_send_success_by_source(self, mock_post):
        """Test WebhookNotifier heading and formatting by source."""
        cases = [
            (
                "arxiv",
                create_article(),
                "✨ New ML/DL Papers Found! ✨\n\n"
                "📄 Test Title\n🔗 http://test.com\n"
                "📝 Test Summary\n\n",
            ),
            (
                "hn",
                create_article(
                    title="HN Title",
                    summary="HN Summary",
                    link="http://hn.com/story",
                    source="hn",
                    author="HN Author",
                    pdf_link="",
                ),
                "🚀 Hacker News 热门讨论\n\n"
                "📄 HN Title\n🔗 http://hn.com/story\n"
                "📝 HN Summary\n\n",
            ),
        ]

        for source, article, expected_text in cases:
            with self.subTest(source=source):
                mock_post.reset_mock()
                setup_successful_post(mock_post)
                self.notifier.send([article])
                self._assert_sent_text(mock_post, expected_text)

    @patch('requests.post')
    def test_send_no_articles(self, mock_post):
        """Test WebhookNotifier sends a reminder when no articles are provided."""
        setup_successful_post(mock_post)

        self.notifier.send([])

        self._assert_sent_text(mock_post, "📭 No new articles this time.")

class MockTranslator(Translator):
    """Mock translator for testing."""
    
    def translate(self, text: str) -> str:
        """Returns a mock Chinese translation."""
        translations = {
            "Test Title": "测试标题",
            "Test Summary": "测试摘要",
            "HN Title": "HN 标题",
            "HN Summary": "HN 摘要",
        }
        return translations.get(text, f"[翻译]{text}")


class TestTelegramNotifierWithTranslation(unittest.TestCase):
    """Tests for TelegramNotifier with translation enabled."""

    def setUp(self):
        self.bot_token = "test_token"
        self.chat_id = "test_chat_id"
        self.translator = MockTranslator()
        self.notifier = TelegramNotifier(self.bot_token, self.chat_id, translator=self.translator)

    @patch('requests.post')
    def test_send_with_translation(self, mock_post):
        """Test that translated content is included in message."""
        setup_successful_post(mock_post)
        self.notifier.send([create_article()])

        # Verify translated content is in the message
        call_args = mock_post.call_args
        message = call_args[1]['json']['text']
        
        self.assertIn("Test Title", message)  # Original title
        self.assertIn("测试标题", message)     # Translated title
        self.assertIn("Test Summary", message)  # Original summary
        self.assertIn("测试摘要", message)      # Translated summary

    @patch('requests.post')
    def test_send_without_summary(self, mock_post):
        """Test message formatting when article has no summary."""
        setup_successful_post(mock_post)
        self.notifier.send([create_article(summary="", pdf_link="")])

        call_args = mock_post.call_args
        message = call_args[1]['json']['text']
        
        self.assertIn("Test Title", message)
        self.assertIn("测试标题", message)
        # Summary emoji should not appear when there's no summary
        self.assertEqual(message.count("📝"), 0)


class TestWebhookNotifierWithTranslation(unittest.TestCase):
    """Tests for WebhookNotifier with translation enabled."""

    def setUp(self):
        self.webhook_url = "https://open.feishu.cn/open-apis/bot/v2/hook/test-webhook"
        self.translator = MockTranslator()
        self.notifier = WebhookNotifier(self.webhook_url, translator=self.translator)

    @patch('requests.post')
    def test_send_with_translation(self, mock_post):
        """Test that translated content is included in webhook message."""
        setup_successful_post(mock_post)
        self.notifier.send([create_article()])

        call_args = mock_post.call_args
        message = call_args[1]['json']['content']['text']
        
        self.assertIn("Test Title", message)
        self.assertIn("测试标题", message)
        self.assertIn("Test Summary", message)
        self.assertIn("测试摘要", message)

    @patch('requests.post')
    def test_send_hn_with_translation(self, mock_post):
        """Test Hacker News articles with translation."""
        setup_successful_post(mock_post)
        self.notifier.send([
            create_article(
                title="HN Title",
                summary="HN Summary",
                link="http://hn.com/story",
                source="hn",
                author="HN Author",
                pdf_link="",
            )
        ])

        call_args = mock_post.call_args
        message = call_args[1]['json']['content']['text']
        
        self.assertIn("HN Title", message)
        self.assertIn("HN 标题", message)
        self.assertIn("HN Summary", message)
        self.assertIn("HN 摘要", message)
        self.assertIn("Hacker News", message)


if __name__ == '__main__':
    unittest.main()
