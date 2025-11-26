import time
import unittest
from unittest.mock import Mock, patch
import requests

from ml_subscriber.core.hn_fetcher import HackerNewsFetcher


class TestHackerNewsFetcher(unittest.TestCase):
    @patch("ml_subscriber.core.hn_fetcher.requests.get")
    def test_fetch_articles_success(self, mock_get):
        top_response = Mock()
        top_response.raise_for_status.return_value = None
        top_response.json.return_value = [123]

        story_response = Mock()
        story_response.raise_for_status.return_value = None
        story_response.json.return_value = {
            "type": "story",
            "title": "Test Story",
            "text": "Story text",
            "url": "https://example.com/story",
            "by": "tester",
            "time":  int(time.time()),
            "score": 42,
            "descendants": 10,
        }

        mock_get.side_effect = [top_response, story_response]

        fetcher = HackerNewsFetcher()
        articles = fetcher.fetch_articles(max_results=1)

        self.assertEqual(len(articles), 1)
        article = articles[0]
        self.assertEqual(article.title, "Test Story")
        self.assertEqual(article.authors, ["tester"])
        self.assertEqual(article.link, "https://example.com/story")
        self.assertEqual(article.metadata.get("source"), "hn")
        self.assertEqual(article.metadata.get("hn_score"), 42)

    @patch("ml_subscriber.core.hn_fetcher.requests.get")
    def test_fetch_articles_request_error(self, mock_get):
        mock_get.side_effect = requests.RequestException("Network error")

        fetcher = HackerNewsFetcher()
        articles = fetcher.fetch_articles(max_results=1)

        self.assertEqual(articles, [])


if __name__ == "__main__":
    unittest.main()
