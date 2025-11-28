import unittest
from unittest.mock import patch, MagicMock
from ml_subscriber.core.notification import TelegramNotifier, WebhookNotifier
from ml_subscriber.core.models import Article

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
        expected_message += "👤 <i>Test Author</i>\n"
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
        expected_message += "👤 <i>HN Author</i>\n"
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
        text_content += "📄 Test Title\n🔗 http://test.com\n👤 Test Author\n"
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
        text_content += "📄 HN Title\n🔗 http://hn.com/story\n👤 HN Author\n"
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

if __name__ == '__main__':
    unittest.main()
