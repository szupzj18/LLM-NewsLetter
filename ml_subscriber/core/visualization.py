from typing import List

from .models import Article

class ArticleVisualizer:
    """Visualizes articles in different formats."""

    def generate_html(self, articles: List[Article], output_filename: str = "articles.html"):
        """
        Generates an HTML file to visualize articles.

        Args:
            articles: A list of Article objects.
            output_filename: The name of the output HTML file.
        """
        html_content = "<html><head><title>ML/DL Articles</title></head><body>"
        html_content += "<h1>ML/DL Articles</h1>"
        for article in articles:
            html_content += f"<h2>{article.title}</h2>"
            authors = ', '.join(article.authors) if article.authors else "Unknown"
            html_content += f"<p><strong>Authors:</strong> {authors}</p>"
            html_content += f"<p>{article.summary}</p>"
            if article.pdf_link:
                html_content += f"<p><a href='{article.pdf_link}'>Read More</a></p>"
            html_content += "<hr>"
        html_content += "</body></html>"

        with open(output_filename, 'w', encoding='utf-8') as f:
            f.write(html_content)
