
import json
from typing import List
from dataclasses import asdict

from .models import Article

class JsonStorage:
    """Handles storage of articles in a JSON file."""

    def save_articles(self, articles: List[Article], file_path: str):
        """
        Saves a list of articles to a JSON file.

        Args:
            articles: A list of Article objects.
            file_path: The path to the JSON file.
        """
        with open(file_path, "w", encoding="utf-8") as f:
            # Convert list of Article objects to a list of dictionaries
            articles_dict = [asdict(article) for article in articles]
            json.dump(articles_dict, f, ensure_ascii=False, indent=4)

    def load_articles(self, file_path: str) -> List[Article]:
        """
        Loads a list of articles from a JSON file.

        Args:
            file_path: The path to the JSON file.

        Returns:
            A list of Article objects.
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                articles_dict = json.load(f)
                # Convert list of dictionaries back to a list of Article objects
                return [Article(**article_data) for article_data in articles_dict]
        except FileNotFoundError:
            return []
        except json.JSONDecodeError:
            # Handle cases where the file is empty or corrupted
            return []

