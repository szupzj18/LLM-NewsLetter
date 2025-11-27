import json
import os
import tempfile
from dataclasses import asdict
from typing import List

from .models import Article


class JsonStorage:
    """Handles storage of articles in a JSON file."""

    def save_articles(self, articles: List[Article], file_path: str):
        """
        Saves a list of articles to a JSON file using atomic write.

        Args:
            articles: A list of Article objects.
            file_path: The path to the JSON file.
        """
        # Convert list of Article objects to a list of dictionaries
        articles_dict = [asdict(article) for article in articles]

        # Use atomic write: write to temp file first, then rename
        dir_name = os.path.dirname(file_path) or "."
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=dir_name, delete=False, suffix=".tmp"
        ) as f:
            json.dump(articles_dict, f, ensure_ascii=False, indent=4)
            temp_path = f.name

        # Atomic rename (on POSIX systems)
        os.replace(temp_path, file_path)

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

