
import unittest
from unittest.mock import patch, Mock
import requests
from ml_subscriber.core.arxiv_fetcher import ArxivFetcher
from ml_subscriber.core.models import Article

class TestArxivFetcher(unittest.TestCase):
    """Tests for the ArxivFetcher class."""

    @patch("ml_subscriber.core.arxiv_fetcher.requests.get")
    def test_fetch_articles_success(self, mock_get):
        """Test successful fetching and parsing of articles."""
        # Create a mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = """
        <feed xmlns=\"http://www.w3.org/2005/Atom\">
          <entry>
            <id>http://example.com/1</id>
            <title>Test Title 1</title>
            <summary>Test Summary 1</summary>
            <author><name>Author 1</name></author>
            <published>2023-10-27T10:00:00Z</published>
            <link title=\"pdf\" href=\"http://example.com/1.pdf\"/>
          </entry>
        </feed>
        """
        mock_get.return_value = mock_response

        fetcher = ArxivFetcher()
        articles = fetcher.fetch_articles("cat:cs.AI", max_results=1)

        self.assertEqual(len(articles), 1)
        self.assertEqual(articles[0].title, "Test Title 1")
        self.assertEqual(articles[0].authors, ["Author 1"])
        self.assertEqual(articles[0].summary, "Test Summary 1")
        self.assertEqual(articles[0].link, "http://example.com/1")
        self.assertEqual(articles[0].published_date, "2023-10-27T10:00:00Z")
        self.assertEqual(articles[0].pdf_link, "http://example.com/1.pdf")

    @patch("ml_subscriber.core.arxiv_fetcher.requests.get")
    def test_fetch_articles_request_error(self, mock_get):
        """Test handling of a request exception."""
        mock_get.side_effect = requests.exceptions.RequestException("Test Error")

        fetcher = ArxivFetcher()
        articles = fetcher.fetch_articles("cat:cs.AI")

        self.assertEqual(len(articles), 0)

if __name__ == "__main__":
    unittest.main()

