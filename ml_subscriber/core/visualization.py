import html
from typing import List
from urllib.parse import quote

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
            # Escape all user-provided content to prevent XSS
            safe_title = html.escape(article.title)
            authors = ', '.join(article.authors) if article.authors else "Unknown"
            safe_authors = html.escape(authors)
            safe_summary = html.escape(article.summary)

            html_content += f"<h2>{safe_title}</h2>"
            html_content += f"<p><strong>Authors:</strong> {safe_authors}</p>"
            html_content += f"<p>{safe_summary}</p>"
            if article.pdf_link:
                # URL encode the link for safe href attribute
                safe_link = html.escape(article.pdf_link, quote=True)
                html_content += f'<p><a href="{safe_link}">Read More</a></p>'
            html_content += "<hr>"
        html_content += "</body></html>"

        with open(output_filename, 'w', encoding='utf-8') as f:
            f.write(html_content)
