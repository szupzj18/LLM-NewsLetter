
import logging
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from .models import Article

logger = logging.getLogger(__name__)


class ArxivFetcher:
    """Fetches and parses articles from ArXiv."""

    BASE_URL = "http://export.arxiv.org/api/query"
    ATOM_NS = "{http://www.w3.org/2005/Atom}"

    def fetch_articles(
        self,
        search_query: str,
        max_results: int = 10,
        days: Optional[int] = None,
    ) -> List[Article]:
        """
        Fetches articles from ArXiv based on a search query.

        Args:
            search_query: The search query for ArXiv.
            max_results: The maximum number of results to return.
            days: If specified, only fetch articles from the last N days.
                  This filters by published date after fetching.

        Returns:
            A list of Article objects.
        """
        params = {
            "search_query": search_query,
            "start": 0,
            "max_results": max_results,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }

        try:
            response = requests.get(self.BASE_URL, params=params)
            response.raise_for_status()  # Raise an exception for bad status codes
            articles = self._parse_xml(response.text)

            # Filter by date if days is specified
            if days is not None:
                articles = self._filter_by_date(articles, days)

            return articles
        except requests.exceptions.RequestException as e:
            logger.exception("Error fetching data from ArXiv")
            return []

    def _filter_by_date(self, articles: List[Article], days: int) -> List[Article]:
        """
        Filter articles to only include those published within the last N days.

        Args:
            articles: List of articles to filter.
            days: Number of days to look back.

        Returns:
            Filtered list of articles.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        filtered = []

        for article in articles:
            if not article.published_date:
                continue
            try:
                pub_date = self._parse_published_date(article.published_date)
                if pub_date >= cutoff:
                    filtered.append(article)
            except ValueError:
                # If date parsing fails, skip the article
                continue

        return filtered

    def _parse_published_date(self, date_str: str) -> datetime:
        """Parse ArXiv published date into a timezone-aware datetime."""
        # ArXiv date format: 2024-01-15T12:00:00Z
        return datetime.fromisoformat(date_str.replace("Z", "+00:00"))

    def _atom_tag(self, tag_name: str) -> str:
        """Build a namespaced Atom tag."""
        return f"{self.ATOM_NS}{tag_name}"

    def _required_text(self, entry: ET.Element, tag_name: str) -> Optional[str]:
        """Extract required text content from entry; returns None when missing."""
        element = entry.find(self._atom_tag(tag_name))
        if element is None or element.text is None:
            return None
        return element.text.strip()

    def _optional_text(self, entry: ET.Element, tag_name: str) -> str:
        """Extract optional text content from entry with empty default."""
        element = entry.find(self._atom_tag(tag_name))
        if element is None or element.text is None:
            return ""
        return element.text.strip()

    def _extract_published_date(self, entry: ET.Element) -> str:
        """Extract published date while preserving current raw field behavior."""
        element = entry.find(self._atom_tag("published"))
        if element is None or element.text is None:
            return ""
        return element.text.strip()

    def _extract_authors(self, entry: ET.Element) -> List[str]:
        """Extract author names from an Atom entry."""
        authors = []
        for author in entry.findall(self._atom_tag("author")):
            name_elem = author.find(self._atom_tag("name"))
            if name_elem is not None and name_elem.text:
                authors.append(name_elem.text)
        return authors

    def _extract_pdf_link(self, entry: ET.Element) -> str:
        """Extract PDF link from an Atom entry."""
        for link_element in entry.findall(self._atom_tag("link")):
            if link_element.get("title") == "pdf":
                return link_element.get("href") or ""
        return ""

    def _normalize_whitespace(self, value: str) -> str:
        """Collapse repeated whitespace for title/summary fields."""
        return " ".join(value.split())

    def _parse_entry(self, entry: ET.Element) -> Optional[Article]:
        """Parse a single Atom entry into an Article."""
        title = self._required_text(entry, "title")
        link = self._required_text(entry, "id")

        # Skip entries with missing required fields
        if title is None or link is None:
            return None

        summary = self._optional_text(entry, "summary")
        published_date = self._extract_published_date(entry)
        authors = self._extract_authors(entry)
        pdf_link = self._extract_pdf_link(entry)

        # Clean up and strip whitespace
        title = self._normalize_whitespace(title)
        summary = self._normalize_whitespace(summary)

        return Article(
            title=title,
            authors=authors,
            summary=summary,
            link=link,
            published_date=published_date,
            pdf_link=pdf_link,
            metadata={"source": "arxiv"},
        )

    def _parse_xml(self, xml_data: str) -> List[Article]:
        """
        Parses XML data from ArXiv into a list of Article objects.

        Args:
            xml_data: The XML data as a string.

        Returns:
            A list of Article objects.
        """
        root = ET.fromstring(xml_data)
        articles = []
        for entry in root.findall(self._atom_tag("entry")):
            article = self._parse_entry(entry)
            if article is not None:
                articles.append(article)
        return articles
