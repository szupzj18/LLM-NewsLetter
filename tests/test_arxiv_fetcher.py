
import unittest
from unittest.mock import patch, Mock
from datetime import datetime, timedelta, timezone
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

    @patch("ml_subscriber.core.arxiv_fetcher.requests.get")
    def test_fetch_articles_missing_title(self, mock_get):
        """Test handling of entries with missing title."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = """
        <feed xmlns=\"http://www.w3.org/2005/Atom\">
          <entry>
            <id>http://example.com/1</id>
            <!-- title is missing -->
            <summary>Test Summary</summary>
            <author><name>Author 1</name></author>
            <published>2023-10-27T10:00:00Z</published>
          </entry>
        </feed>
        """
        mock_get.return_value = mock_response

        fetcher = ArxivFetcher()
        articles = fetcher.fetch_articles("cat:cs.AI", max_results=1)

        # Entry with missing title should be skipped
        self.assertEqual(len(articles), 0)

    @patch("ml_subscriber.core.arxiv_fetcher.requests.get")
    def test_fetch_articles_missing_link(self, mock_get):
        """Test handling of entries with missing link/id."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = """
        <feed xmlns=\"http://www.w3.org/2005/Atom\">
          <entry>
            <!-- id is missing -->
            <title>Test Title</title>
            <summary>Test Summary</summary>
            <author><name>Author 1</name></author>
            <published>2023-10-27T10:00:00Z</published>
          </entry>
        </feed>
        """
        mock_get.return_value = mock_response

        fetcher = ArxivFetcher()
        articles = fetcher.fetch_articles("cat:cs.AI", max_results=1)

        # Entry with missing link should be skipped
        self.assertEqual(len(articles), 0)

    @patch("ml_subscriber.core.arxiv_fetcher.requests.get")
    def test_fetch_articles_missing_optional_fields(self, mock_get):
        """Test handling of entries with missing optional fields (summary, published, authors)."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = """
        <feed xmlns=\"http://www.w3.org/2005/Atom\">
          <entry>
            <id>http://example.com/1</id>
            <title>Test Title</title>
            <!-- summary, published, and authors are missing -->
          </entry>
        </feed>
        """
        mock_get.return_value = mock_response

        fetcher = ArxivFetcher()
        articles = fetcher.fetch_articles("cat:cs.AI", max_results=1)

        # Entry should still be parsed with empty optional fields
        self.assertEqual(len(articles), 1)
        self.assertEqual(articles[0].title, "Test Title")
        self.assertEqual(articles[0].summary, "")
        self.assertEqual(articles[0].published_date, "")
        self.assertEqual(articles[0].authors, [])
        self.assertEqual(articles[0].pdf_link, "")

    @patch("ml_subscriber.core.arxiv_fetcher.requests.get")
    def test_fetch_articles_empty_feed(self, mock_get):
        """Test handling of an empty feed."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = """
        <feed xmlns=\"http://www.w3.org/2005/Atom\">
        </feed>
        """
        mock_get.return_value = mock_response

        fetcher = ArxivFetcher()
        articles = fetcher.fetch_articles("cat:cs.AI", max_results=1)

        self.assertEqual(len(articles), 0)

    @patch("ml_subscriber.core.arxiv_fetcher.requests.get")
    def test_fetch_articles_with_days_filter(self, mock_get):
        """Test filtering articles by days."""
        # Create dates: one from today, one from 3 days ago
        today = datetime.now(timezone.utc)
        old_date = today - timedelta(days=3)
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = f"""
        <feed xmlns=\"http://www.w3.org/2005/Atom\">
          <entry>
            <id>http://example.com/1</id>
            <title>Recent Article</title>
            <summary>Recent Summary</summary>
            <author><name>Author 1</name></author>
            <published>{today.strftime('%Y-%m-%dT%H:%M:%SZ')}</published>
          </entry>
          <entry>
            <id>http://example.com/2</id>
            <title>Old Article</title>
            <summary>Old Summary</summary>
            <author><name>Author 2</name></author>
            <published>{old_date.strftime('%Y-%m-%dT%H:%M:%SZ')}</published>
          </entry>
        </feed>
        """
        mock_get.return_value = mock_response

        fetcher = ArxivFetcher()
        # Only fetch articles from last 1 day
        articles = fetcher.fetch_articles("cat:cs.AI", max_results=10, days=1)

        # Only the recent article should be returned
        self.assertEqual(len(articles), 1)
        self.assertEqual(articles[0].title, "Recent Article")

    @patch("ml_subscriber.core.arxiv_fetcher.requests.get")
    def test_fetch_articles_days_filter_includes_boundary(self, mock_get):
        """Test that days filter includes articles exactly at the boundary."""
        # Create a date exactly 1 day ago (should be included with days=1)
        exactly_one_day_ago = datetime.now(timezone.utc) - timedelta(days=1, seconds=-1)
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = f"""
        <feed xmlns=\"http://www.w3.org/2005/Atom\">
          <entry>
            <id>http://example.com/1</id>
            <title>Boundary Article</title>
            <summary>Summary</summary>
            <author><name>Author</name></author>
            <published>{exactly_one_day_ago.strftime('%Y-%m-%dT%H:%M:%SZ')}</published>
          </entry>
        </feed>
        """
        mock_get.return_value = mock_response

        fetcher = ArxivFetcher()
        articles = fetcher.fetch_articles("cat:cs.AI", max_results=10, days=1)

        self.assertEqual(len(articles), 1)

    @patch("ml_subscriber.core.arxiv_fetcher.requests.get")
    def test_fetch_articles_without_days_filter(self, mock_get):
        """Test that all articles are returned when days is not specified."""
        old_date = datetime.now(timezone.utc) - timedelta(days=30)
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = f"""
        <feed xmlns=\"http://www.w3.org/2005/Atom\">
          <entry>
            <id>http://example.com/1</id>
            <title>Old Article</title>
            <summary>Summary</summary>
            <author><name>Author</name></author>
            <published>{old_date.strftime('%Y-%m-%dT%H:%M:%SZ')}</published>
          </entry>
        </feed>
        """
        mock_get.return_value = mock_response

        fetcher = ArxivFetcher()
        # No days filter
        articles = fetcher.fetch_articles("cat:cs.AI", max_results=10)

        # Old article should still be returned
        self.assertEqual(len(articles), 1)

    @patch("ml_subscriber.core.arxiv_fetcher.requests.get")
    def test_fetch_articles_days_filter_skips_invalid_dates(self, mock_get):
        """Test that articles with invalid dates are skipped when filtering."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = """
        <feed xmlns=\"http://www.w3.org/2005/Atom\">
          <entry>
            <id>http://example.com/1</id>
            <title>Invalid Date Article</title>
            <summary>Summary</summary>
            <author><name>Author</name></author>
            <published>not-a-valid-date</published>
          </entry>
        </feed>
        """
        mock_get.return_value = mock_response

        fetcher = ArxivFetcher()
        articles = fetcher.fetch_articles("cat:cs.AI", max_results=10, days=1)

        # Article with invalid date should be skipped
        self.assertEqual(len(articles), 0)

    @patch("ml_subscriber.core.arxiv_fetcher.requests.get")
    def test_fetch_articles_days_filter_skips_empty_dates(self, mock_get):
        """Test that articles with empty dates are skipped when filtering."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = """
        <feed xmlns=\"http://www.w3.org/2005/Atom\">
          <entry>
            <id>http://example.com/1</id>
            <title>No Date Article</title>
            <summary>Summary</summary>
            <author><name>Author</name></author>
          </entry>
        </feed>
        """
        mock_get.return_value = mock_response

        fetcher = ArxivFetcher()
        articles = fetcher.fetch_articles("cat:cs.AI", max_results=10, days=1)

        # Article without date should be skipped when filtering
        self.assertEqual(len(articles), 0)


if __name__ == "__main__":
    unittest.main()

