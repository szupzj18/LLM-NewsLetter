from dataclasses import dataclass, field
from typing import Dict, List, Protocol


@dataclass
class Article:
    """Represents a research or news article."""

    title: str
    authors: List[str]
    summary: str
    link: str
    published_date: str
    pdf_link: str
    metadata: Dict[str, object] = field(default_factory=dict)


class ContentSource(Protocol):
    """Protocol for sources that can fetch articles."""

    def fetch_articles(self, search_query: str, max_results: int = 10) -> List[Article]:
        ...
