
import unittest
import json
import os
import tempfile
from ml_subscriber.core.storage import JsonStorage
from ml_subscriber.core.arxiv_fetcher import Article

class TestJsonStorage(unittest.TestCase):
    """Tests for the JsonStorage class."""

    def setUp(self):
        """Set up a temporary file for testing."""
        self.temp_file = tempfile.NamedTemporaryFile(delete=False, mode='w+', encoding='utf-8')
        self.temp_filename = self.temp_file.name
        self.storage = JsonStorage()

    def tearDown(self):
        """Clean up the temporary file."""
        self.temp_file.close()
        os.unlink(self.temp_filename)

    def test_save_and_load_articles(self):
        """Test saving and loading articles to/from a JSON file."""
        articles = [
            Article(
                title="Test Title 1",
                authors=["Author 1"],
                summary="Summary 1",
                link="http://example.com/1",
                published_date="2023-10-27T10:00:00Z",
                pdf_link="http://example.com/1.pdf"
            )
        ]

        # Save articles
        self.storage.save_articles(articles, self.temp_filename)

        # Load articles
        loaded_articles = self.storage.load_articles(self.temp_filename)

        self.assertEqual(len(loaded_articles), 1)
        self.assertEqual(loaded_articles[0].title, "Test Title 1")

    def test_load_from_nonexistent_file(self):
        """Test loading from a file that does not exist."""
        loaded_articles = self.storage.load_articles("nonexistent.json")
        self.assertEqual(len(loaded_articles), 0)

    def test_load_from_empty_file(self):
        """Test loading from an empty or invalid JSON file."""
        # First, ensure the file is empty
        self.temp_file.truncate(0)
        loaded_articles = self.storage.load_articles(self.temp_filename)
        self.assertEqual(len(loaded_articles), 0)

if __name__ == "__main__":
    unittest.main()
