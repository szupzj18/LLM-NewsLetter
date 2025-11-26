
import unittest
from unittest.mock import patch, MagicMock
from ml_subscriber.core.notification import TelegramNotifier
from ml_subscriber.core.arxiv_fetcher import Article

class TestTelegramNotifier(unittest.TestCase):

    def setUp(self):
        self.bot_token = "test_token"
        self.chat_id = "test_chat_id"
        self.notifier = TelegramNotifier(self.bot_token, self.chat_id)

    @patch('requests.post')
    def test_send_success(self, mock_post):
        """Test that send method calls requests.post with correct data."""
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
                pdf_link="http://test.com/test.pdf"
            )
        ]
        self.notifier.send(articles)

        expected_message = "✨ <b>New ML/DL Papers Found!</b> ✨\n\n"
        expected_message += "📄 <b><a href=\"http://test.com\">Test Title</a></b>\n"
        expected_message += "👤 <i>Test Author</i>\n\n"

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
        """Test that send method does not call requests.post if no articles are provided."""
        self.notifier.send([])
        mock_post.assert_not_called()

if __name__ == '__main__':
    unittest.main()

