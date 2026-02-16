import unittest
from unittest.mock import patch, Mock
from datetime import datetime, timedelta, timezone
import requests

from ml_subscriber.core.arxiv_fetcher import ArxivFetcher


ATOM_NS = "http://www.w3.org/2005/Atom"


def build_entry(
    article_id="http://example.com/1",
    title="Test Title",
    summary="Test Summary",
    author="Author",
    published="2023-10-27T10:00:00Z",
    pdf_link=None,
    include_id=True,
    include_title=True,
    include_summary=True,
    include_author=True,
    include_published=True,
):
    """Build an Atom entry snippet for tests."""
    parts = ["<entry>"]
    if include_id:
        parts.append(f"<id>{article_id}</id>")
    if include_title:
        parts.append(f"<title>{title}</title>")
    if include_summary:
        parts.append(f"<summary>{summary}</summary>")
    if include_author:
        parts.append(f"<author><name>{author}</name></author>")
    if include_published:
        parts.append(f"<published>{published}</published>")
    if pdf_link is not None:
        parts.append(f'<link title="pdf" href="{pdf_link}"/>')
    parts.append("</entry>")
    return "\n".join(parts)


def build_feed(*entries):
    """Build an Atom feed XML string from entries."""
    entries_xml = "\n".join(entries)
    return f'<feed xmlns="{ATOM_NS}">\n{entries_xml}\n</feed>'


class TestArxivFetcher(unittest.TestCase):
    """Tests for the ArxivFetcher class."""

    def _mock_feed(self, mock_get, *entries):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = build_feed(*entries)
        mock_get.return_value = mock_response

    @patch("ml_subscriber.core.arxiv_fetcher.requests.get")
    def test_fetch_articles_success(self, mock_get):
        """Test successful fetching and parsing of articles."""
        self._mock_feed(
            mock_get,
            build_entry(
                title="Test Title 1",
                summary="Test Summary 1",
                author="Author 1",
                pdf_link="http://example.com/1.pdf",
            ),
        )

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
        self._mock_feed(
            mock_get,
            build_entry(include_title=False, author="Author 1", pdf_link=None),
        )

        fetcher = ArxivFetcher()
        articles = fetcher.fetch_articles("cat:cs.AI", max_results=1)

        # Entry with missing title should be skipped
        self.assertEqual(len(articles), 0)

    @patch("ml_subscriber.core.arxiv_fetcher.requests.get")
    def test_fetch_articles_missing_link(self, mock_get):
        """Test handling of entries with missing link/id."""
        self._mock_feed(
            mock_get,
            build_entry(include_id=False, author="Author 1", pdf_link=None),
        )

        fetcher = ArxivFetcher()
        articles = fetcher.fetch_articles("cat:cs.AI", max_results=1)

        # Entry with missing link should be skipped
        self.assertEqual(len(articles), 0)

    @patch("ml_subscriber.core.arxiv_fetcher.requests.get")
    def test_fetch_articles_missing_optional_fields(self, mock_get):
        """Test handling of entries with missing optional fields (summary, published, authors)."""
        self._mock_feed(
            mock_get,
            build_entry(
                title="Test Title",
                include_summary=False,
                include_published=False,
                include_author=False,
                pdf_link=None,
            ),
        )

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
        self._mock_feed(mock_get)

        fetcher = ArxivFetcher()
        articles = fetcher.fetch_articles("cat:cs.AI", max_results=1)

        self.assertEqual(len(articles), 0)

    @patch("ml_subscriber.core.arxiv_fetcher.requests.get")
    def test_fetch_articles_with_days_filter(self, mock_get):
        """Test filtering articles by days."""
        # Create dates: one from today, one from 3 days ago
        today = datetime.now(timezone.utc)
        old_date = today - timedelta(days=3)

        self._mock_feed(
            mock_get,
            build_entry(
                article_id="http://example.com/1",
                title="Recent Article",
                summary="Recent Summary",
                author="Author 1",
                published=today.strftime("%Y-%m-%dT%H:%M:%SZ"),
            ),
            build_entry(
                article_id="http://example.com/2",
                title="Old Article",
                summary="Old Summary",
                author="Author 2",
                published=old_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
            ),
        )

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

        self._mock_feed(
            mock_get,
            build_entry(
                title="Boundary Article",
                published=exactly_one_day_ago.strftime("%Y-%m-%dT%H:%M:%SZ"),
            ),
        )

        fetcher = ArxivFetcher()
        articles = fetcher.fetch_articles("cat:cs.AI", max_results=10, days=1)

        self.assertEqual(len(articles), 1)

    @patch("ml_subscriber.core.arxiv_fetcher.requests.get")
    def test_fetch_articles_without_days_filter(self, mock_get):
        """Test that all articles are returned when days is not specified."""
        old_date = datetime.now(timezone.utc) - timedelta(days=30)

        self._mock_feed(
            mock_get,
            build_entry(
                title="Old Article",
                published=old_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
            ),
        )

        fetcher = ArxivFetcher()
        # No days filter
        articles = fetcher.fetch_articles("cat:cs.AI", max_results=10)

        # Old article should still be returned
        self.assertEqual(len(articles), 1)

    @patch("ml_subscriber.core.arxiv_fetcher.requests.get")
    def test_fetch_articles_days_filter_skips_invalid_dates(self, mock_get):
        """Test that articles with invalid dates are skipped when filtering."""
        self._mock_feed(
            mock_get,
            build_entry(title="Invalid Date Article", published="not-a-valid-date"),
        )

        fetcher = ArxivFetcher()
        articles = fetcher.fetch_articles("cat:cs.AI", max_results=10, days=1)

        # Article with invalid date should be skipped
        self.assertEqual(len(articles), 0)

    @patch("ml_subscriber.core.arxiv_fetcher.requests.get")
    def test_fetch_articles_days_filter_skips_empty_dates(self, mock_get):
        """Test that articles with empty dates are skipped when filtering."""
        self._mock_feed(
            mock_get,
            build_entry(title="No Date Article", include_published=False),
        )

        fetcher = ArxivFetcher()
        articles = fetcher.fetch_articles("cat:cs.AI", max_results=10, days=1)

        # Article without date should be skipped when filtering
        self.assertEqual(len(articles), 0)

    @patch("ml_subscriber.core.arxiv_fetcher.requests.get")
    def test_fetch_articles_days_filter_parses_whitespace_published_date(self, mock_get):
        """Test that surrounding whitespace in published date is safely handled."""
        today = datetime.now(timezone.utc)
        published_with_whitespace = f"  {today.strftime('%Y-%m-%dT%H:%M:%SZ')}  "

        self._mock_feed(
            mock_get,
            build_entry(
                title="Whitespace Date Article",
                published=published_with_whitespace,
            ),
        )

        fetcher = ArxivFetcher()
        articles = fetcher.fetch_articles("cat:cs.AI", max_results=10, days=1)

        self.assertEqual(len(articles), 1)
        self.assertEqual(articles[0].title, "Whitespace Date Article")


if __name__ == "__main__":
    unittest.main()

