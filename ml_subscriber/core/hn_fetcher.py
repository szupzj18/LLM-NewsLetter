import logging
import time
from typing import List, Optional

import requests

from .models import Article

logger = logging.getLogger(__name__)


class HackerNewsFetcher:
    """Fetches top stories from Hacker News and maps them to Articles."""

    TOP_STORIES_URL = "https://hacker-news.firebaseio.com/v0/topstories.json"
    ITEM_URL = "https://hacker-news.firebaseio.com/v0/item/{item_id}.json"

    def __init__(self, max_item_age_days: int = 7):
        self.max_item_age_seconds = max_item_age_days * 24 * 60 * 60

    def fetch_articles(self, search_query: str = "", max_results: int = 10) -> List[Article]:
        """Fetches top Hacker News stories and maps them to Article objects."""
        try:
            response = requests.get(self.TOP_STORIES_URL, timeout=10)
            response.raise_for_status()
            story_ids = response.json()[: max_results * 2]
        except requests.RequestException as exc:
            logger.exception("Error fetching top stories from Hacker News")
            return []

        articles: List[Article] = []
        now = time.time()
        for item_id in story_ids:
            if len(articles) >= max_results:
                break

            article = self._fetch_story(item_id)
            if not article:
                continue

            # Filter out very old stories if configured
            try:
                published_ts = float(article.metadata.get("hn_timestamp", 0))
            except (TypeError, ValueError):
                published_ts = 0

            if (
                self.max_item_age_seconds > 0
                and published_ts
                and (now - published_ts) > self.max_item_age_seconds
            ):
                continue

            articles.append(article)

        return articles

    def _fetch_story(self, item_id: int) -> Optional[Article]:
        """Fetches an individual story and converts it to an Article."""
        try:
            response = requests.get(self.ITEM_URL.format(item_id=item_id), timeout=10)
            response.raise_for_status()
            data = response.json()
        except requests.RequestException:
            return None

        if not data or data.get("type") != "story":
            return None

        title = data.get("title") or "(no title)"
        summary = data.get("text") or "Hacker News story"
        url = data.get("url") or f"https://news.ycombinator.com/item?id={item_id}"
        author = data.get("by") or "Unknown"
        timestamp = data.get("time", 0)
        published_date = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(timestamp)) if timestamp else ""

        metadata = {
            "source": "hn",
            "hn_id": item_id,
            "hn_score": data.get("score", 0),
            "hn_descendants": data.get("descendants", 0),
            "hn_timestamp": timestamp,
            "hn_url": url,
        }

        return Article(
            title=title,
            authors=[author] if author else [],
            summary=summary,
            link=url,
            published_date=published_date,
            pdf_link="",
            metadata=metadata,
        )
