# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## High-level code architecture and structure

This project is a Python application for subscribing to and tracking the latest information in the machine learning (ML) and deep learning (DL) fields. It supports fetching articles from multiple sources (ArXiv, Hacker News), translating content, and sending notifications through various channels.

### Core Modules

The core logic is organized in `ml_subscriber/core/`:

-   **`models.py`**: Defines the `Article` dataclass and `ContentSource` protocol. The `Article` class represents a research or news article with fields like title, authors, summary, link, published_date, pdf_link, and metadata.

-   **`arxiv_fetcher.py`**: Fetches and parses articles from the ArXiv API. The `ArxivFetcher` class handles API requests and XML response parsing. Supports filtering by date range.

-   **`hn_fetcher.py`**: Fetches top stories from Hacker News using Firebase API. The `HackerNewsFetcher` class maps HN stories to the unified `Article` format.

-   **`storage.py`**: Handles article persistence. The `JsonStorage` class saves and loads `Article` objects to/from JSON files.

-   **`translator.py`**: Provides translation capabilities with multiple backends:
    -   `DeepLTranslator`: Uses DeepL API (higher quality, requires API key)
    -   `GoogleFreeTranslator`: Uses free Google Translate
    -   `NoOpTranslator`: Pass-through translator (no translation)
    -   `create_translator()`: Factory function to create appropriate translator

-   **`notification.py`**: Handles sending article notifications:
    -   `Notifier`: Abstract base class for notifiers
    -   `ArticleNotifier`: Base class with shared helpers for article formatting
    -   `TelegramNotifier`: Sends notifications via Telegram Bot API (HTML/MarkdownV2)
    -   `WebhookNotifier`: Sends notifications via webhook (supports Feishu/Lark)

-   **`visualization.py`**: The `ArticleVisualizer` class generates HTML pages to visualize articles.

### Main Entry Point

`main.py` is the CLI entry point with three main commands:
-   `--fetch`: Fetch articles from a source (arxiv/hn) and optionally send notifications
-   `--notify`: Send notifications for previously stored articles
-   `--visualize`: Generate HTML visualization

### Testing

The project uses Python's `unittest` framework. Tests are in `tests/` directory and mock external dependencies (network requests, file I/O).

## Common development tasks

### Running the application

```bash
# Fetch ArXiv papers and notify via Telegram
python3 main.py --fetch --source arxiv --notifier telegram

# Fetch Hacker News stories
python3 main.py --fetch --source hn --json-output output/hn_articles.json

# Generate HTML visualization
python3 main.py --visualize --output output/articles.html

# Send notifications for stored articles
python3 main.py --notify --notifier all
```

### Running tests

To run the full test suite:

```bash
python3 -m unittest discover tests
```

### Environment Variables

| Variable | Description |
|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | Telegram Bot API token |
| `TELEGRAM_CHAT_ID` | Telegram chat ID for notifications |
| `WEBHOOK_URL` | Feishu/Lark webhook URL |
| `DEEPL_API_KEY` | DeepL API key (optional, for high-quality translation) |
| `USE_FREE_TRANSLATOR` | Set to "false" to disable free Google translation |

## Code conventions

-   All content source fetchers implement the `ContentSource` protocol
-   All notifiers inherit from `Notifier` abstract base class
-   All translators inherit from `Translator` abstract base class
-   Use factory functions (e.g., `create_translator()`) for creating instances with configuration

## Documentation maintenance

When making code changes, check whether `Agents.md` needs to be updated. Specifically:

-   **Adding/removing/renaming a core module** — update the "How to Extend the Project" and "Where to Find Things" sections
-   **Changing extension patterns** (new ABC, new protocol, new factory) — update the "Key Design Patterns" section
-   **Changing error handling or security conventions** — update the "Coding Rules" section

Do NOT duplicate content that already lives in this file (CLAUDE.md). Agents.md should only contain design patterns, extension guides, and coding rules that help agents modify the codebase.
