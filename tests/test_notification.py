import unittest
from unittest.mock import patch, MagicMock
from ml_subscriber.core.notification import TelegramNotifier, WebhookNotifier
from ml_subscriber.core.models import Article
from ml_subscriber.core.translator import Translator

class TestTelegramNotifier(unittest.TestCase):

    def setUp(self):
        self.bot_token = "test_token"
        self.chat_id = "test_chat_id"
        self.notifier = TelegramNotifier(self.bot_token, self.chat_id)

    @patch('requests.post')
    def test_send_success_arxiv(self, mock_post):
        """Test Telegram heading for ArXiv articles."""
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        articles = [
            Article(
                title="Test Title",
                authors=["Test Author"],
                summary="Test Summary",
                link="http://test.com",
                published_date="2023-10-27T10:00:00Z",
                pdf_link="http://test.com/test.pdf",
                metadata={"source": "arxiv"}
            )
        ]
        self.notifier.send(articles)

        expected_message = "✨ <b>New ML/DL Papers Found!</b> ✨\n\n"
        expected_message += "📄 <b><a href=\"http://test.com\">Test Title</a></b>\n"
        expected_message += "📝 Test Summary\n\n"

        expected_payload = {
            'chat_id': self.chat_id,
            'text': expected_message,
            'parse_mode': 'HTML'
        }

        mock_post.assert_called_once_with(
            f"https://api.telegram.org/bot{self.bot_token}/sendMessage",
            json=expected_payload
        )

    @patch('requests.post')
    def test_send_success_hn(self, mock_post):
        """Test Telegram heading for Hacker News articles."""
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        articles = [
            Article(
                title="HN Title",
                authors=["HN Author"],
                summary="HN Summary",
                link="http://hn.com/story",
                published_date="2023-10-27T10:00:00Z",
                pdf_link="",
                metadata={"source": "hn"}
            )
        ]
        self.notifier.send(articles)

        expected_message = "🚀 <b>Hacker News 热门讨论</b>\n\n"
        expected_message += "📄 <b><a href=\"http://hn.com/story\">HN Title</a></b>\n"
        expected_message += "📝 HN Summary\n\n"

        expected_payload = {
            'chat_id': self.chat_id,
            'text': expected_message,
            'parse_mode': 'HTML'
        }

        mock_post.assert_called_once_with(
            f"https://api.telegram.org/bot{self.bot_token}/sendMessage",
            json=expected_payload
        )

    @patch('requests.post')
    def test_send_no_articles(self, mock_post):
        """Test that send method sends a reminder when no articles are provided."""
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        self.notifier.send([])

        expected_payload = {
            'chat_id': self.chat_id,
            'text': "📭 <b>No new articles this time.</b>",
            'parse_mode': 'HTML'
        }

        mock_post.assert_called_once_with(
            f"https://api.telegram.org/bot{self.bot_token}/sendMessage",
            json=expected_payload
        )

class TestWebhookNotifier(unittest.TestCase):

    def setUp(self):
        self.webhook_url = "http://test-webhook.com"
        self.notifier = WebhookNotifier(self.webhook_url)

    @patch('requests.post')
    def test_send_success_arxiv(self, mock_post):
        """Test WebhookNotifier with ArXiv articles."""
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        articles = [
            Article(
                title="Test Title",
                authors=["Test Author"],
                summary="Test Summary",
                link="http://test.com",
                published_date="2023-10-27T10:00:00Z",
                pdf_link="http://test.com/test.pdf",
                metadata={"source": "arxiv"}
            )
        ]
        self.notifier.send(articles)

        text_content = "✨ New ML/DL Papers Found! ✨\n\n"
        text_content += "📄 Test Title\n🔗 http://test.com\n"
        text_content += "📝 Test Summary\n\n"
        expected_payload = {
            "msg_type": "text",
            "content": {
                "text": text_content
            }
        }

        mock_post.assert_called_once_with(self.webhook_url, json=expected_payload)

    @patch('requests.post')
    def test_send_success_hn(self, mock_post):
        """Test WebhookNotifier with Hacker News articles."""
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        articles = [
            Article(
                title="HN Title",
                authors=["HN Author"],
                summary="HN Summary",
                link="http://hn.com/story",
                published_date="2023-10-27T10:00:00Z",
                pdf_link="",
                metadata={"source": "hn"}
            )
        ]
        self.notifier.send(articles)

        text_content = "🚀 Hacker News 热门讨论\n\n"
        text_content += "📄 HN Title\n🔗 http://hn.com/story\n"
        text_content += "📝 HN Summary\n\n"
        expected_payload = {
            "msg_type": "text",
            "content": {
                "text": text_content
            }
        }

        mock_post.assert_called_once_with(self.webhook_url, json=expected_payload)

    @patch('requests.post')
    def test_send_no_articles(self, mock_post):
        """Test WebhookNotifier sends a reminder when no articles are provided."""
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        self.notifier.send([])

        expected_payload = {
            "msg_type": "text",
            "content": {
                "text": "📭 No new articles this time."
            }
        }

        mock_post.assert_called_once_with(self.webhook_url, json=expected_payload)

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
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        articles = [
            Article(
                title="Test Title",
                authors=["Test Author"],
                summary="Test Summary",
                link="http://test.com",
                published_date="2023-10-27T10:00:00Z",
                pdf_link="http://test.com/test.pdf",
                metadata={"source": "arxiv"}
            )
        ]
        self.notifier.send(articles)

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
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        articles = [
            Article(
                title="Test Title",
                authors=["Test Author"],
                summary="",
                link="http://test.com",
                published_date="2023-10-27T10:00:00Z",
                pdf_link="",
                metadata={"source": "arxiv"}
            )
        ]
        self.notifier.send(articles)

        call_args = mock_post.call_args
        message = call_args[1]['json']['text']
        
        self.assertIn("Test Title", message)
        self.assertIn("测试标题", message)
        # Summary emoji should not appear when there's no summary
        self.assertEqual(message.count("📝"), 0)


class TestWebhookNotifierWithTranslation(unittest.TestCase):
    """Tests for WebhookNotifier with translation enabled."""

    def setUp(self):
        self.webhook_url = "http://test-webhook.com"
        self.translator = MockTranslator()
        self.notifier = WebhookNotifier(self.webhook_url, translator=self.translator)

    @patch('requests.post')
    def test_send_with_translation(self, mock_post):
        """Test that translated content is included in webhook message."""
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        articles = [
            Article(
                title="Test Title",
                authors=["Test Author"],
                summary="Test Summary",
                link="http://test.com",
                published_date="2023-10-27T10:00:00Z",
                pdf_link="http://test.com/test.pdf",
                metadata={"source": "arxiv"}
            )
        ]
        self.notifier.send(articles)

        call_args = mock_post.call_args
        message = call_args[1]['json']['content']['text']
        
        self.assertIn("Test Title", message)
        self.assertIn("测试标题", message)
        self.assertIn("Test Summary", message)
        self.assertIn("测试摘要", message)

    @patch('requests.post')
    def test_send_hn_with_translation(self, mock_post):
        """Test Hacker News articles with translation."""
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        articles = [
            Article(
                title="HN Title",
                authors=["HN Author"],
                summary="HN Summary",
                link="http://hn.com/story",
                published_date="2023-10-27T10:00:00Z",
                pdf_link="",
                metadata={"source": "hn"}
            )
        ]
        self.notifier.send(articles)

        call_args = mock_post.call_args
        message = call_args[1]['json']['content']['text']
        
        self.assertIn("HN Title", message)
        self.assertIn("HN 标题", message)
        self.assertIn("HN Summary", message)
        self.assertIn("HN 摘要", message)
        self.assertIn("Hacker News", message)


if __name__ == '__main__':
    unittest.main()
