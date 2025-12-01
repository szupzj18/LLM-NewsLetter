
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from .models import Article


class ArxivFetcher:
    """Fetches and parses articles from ArXiv."""

    BASE_URL = "http://export.arxiv.org/api/query"

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
            print(f"Error fetching data from ArXiv: {e}")
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
                # ArXiv date format: 2024-01-15T12:00:00Z
                pub_date = datetime.fromisoformat(
                    article.published_date.replace("Z", "+00:00")
                )
                if pub_date >= cutoff:
                    filtered.append(article)
            except ValueError:
                # If date parsing fails, skip the article
                continue

        return filtered

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
        for entry in root.findall("{http://www.w3.org/2005/Atom}entry"):
            # Safely extract text with None checks
            title_elem = entry.find("{http://www.w3.org/2005/Atom}title")
            link_elem = entry.find("{http://www.w3.org/2005/Atom}id")
            summary_elem = entry.find("{http://www.w3.org/2005/Atom}summary")
            published_elem = entry.find("{http://www.w3.org/2005/Atom}published")

            # Skip entries with missing required fields
            if title_elem is None or title_elem.text is None:
                continue
            if link_elem is None or link_elem.text is None:
                continue

            title = title_elem.text.strip()
            link = link_elem.text.strip()
            summary = summary_elem.text.strip() if summary_elem is not None and summary_elem.text else ""
            published_date = published_elem.text if published_elem is not None and published_elem.text else ""

            authors = []
            for author in entry.findall("{http://www.w3.org/2005/Atom}author"):
                name_elem = author.find("{http://www.w3.org/2005/Atom}name")
                if name_elem is not None and name_elem.text:
                    authors.append(name_elem.text)

            pdf_link = ""
            for link_element in entry.findall("{http://www.w3.org/2005/Atom}link"):
                if link_element.get("title") == "pdf":
                    pdf_link = link_element.get("href") or ""
                    break

            # Clean up and strip whitespace
            title = " ".join(title.split())
            summary = " ".join(summary.split())

            articles.append(
                Article(
                    title=title,
                    authors=authors,
                    summary=summary,
                    link=link,
                    published_date=published_date,
                    pdf_link=pdf_link,
                    metadata={"source": "arxiv"},
                )
            )
        return articles
