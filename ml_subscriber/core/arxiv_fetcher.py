
import requests
import xml.etree.ElementTree as ET
from typing import List

from .models import Article


class ArxivFetcher:
    """Fetches and parses articles from ArXiv."""

    BASE_URL = "http://export.arxiv.org/api/query"

    def fetch_articles(self, search_query: str, max_results: int = 10) -> List[Article]:
        """
        Fetches articles from ArXiv based on a search query.

        Args:
            search_query: The search query for ArXiv.
            max_results: The maximum number of results to return.

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
            return self._parse_xml(response.text)
        except requests.exceptions.RequestException as e:
            print(f"Error fetching data from ArXiv: {e}")
            return []

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
            title = entry.find("{http://www.w3.org/2005/Atom}title").text.strip()
            link = entry.find("{http://www.w3.org/2005/Atom}id").text.strip()
            summary = entry.find("{http://www.w3.org/2005/Atom}summary").text.strip()
            published_date = entry.find("{http://www.w3.org/2005/Atom}published").text

            authors = [
                author.find("{http://www.w3.org/2005/Atom}name").text
                for author in entry.findall("{http://www.w3.org/2005/Atom}author")
            ]

            pdf_link = ""
            for link_element in entry.findall("{http://www.w3.org/2005/Atom}link"):
                if link_element.get("title") == "pdf":
                    pdf_link = link_element.get("href")
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
