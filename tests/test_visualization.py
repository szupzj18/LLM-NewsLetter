import unittest
import os
import tempfile
from ml_subscriber.core.visualization import ArticleVisualizer
from ml_subscriber.core.arxiv_fetcher import Article

class TestArticleVisualizer(unittest.TestCase):
    """Tests for the ArticleVisualizer class."""

    def setUp(self):
        """Set up a temporary file for testing."""
        self.temp_file = tempfile.NamedTemporaryFile(delete=False, mode='w+', encoding='utf-8', suffix='.html')
        self.temp_filename = self.temp_file.name
        self.visualizer = ArticleVisualizer()

    def tearDown(self):
        """Clean up the temporary file."""
        self.temp_file.close()
        os.unlink(self.temp_filename)

    def test_generate_html(self):
        """Test generating an HTML file from a list of articles."""
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

        self.visualizer.generate_html(articles, self.temp_filename)

        with open(self.temp_filename, 'r', encoding='utf-8') as f:
            content = f.read()
            self.assertIn("<h1>ArXiv Articles</h1>", content)
            self.assertIn("<h2>Test Title 1</h2>", content)
            self.assertIn("<p><strong>Authors:</strong> Author 1</p>", content)
            self.assertIn("<p>Summary 1</p>", content)
            self.assertIn("<p><a href='http://example.com/1.pdf'>Read More</a></p>", content)

    def test_generate_html_no_articles(self):
        """Test generating an HTML file with no articles."""
        articles = []

        self.visualizer.generate_html(articles, self.temp_filename)

        with open(self.temp_filename, 'r', encoding='utf-8') as f:
            content = f.read()
            self.assertIn("<h1>ArXiv Articles</h1>", content)
            self.assertNotIn("<h2>", content)

if __name__ == "__main__":
    unittest.main()
