# Agents.md

This document provides guidance for AI agents (Claude, GPT, etc.) working with this codebase.

## Project Overview

This is an ML/DL news subscription system that:
1. Fetches articles from multiple sources (ArXiv, Hacker News)
2. Stores them in JSON format
3. Translates content (via DeepL or Google Translate)
4. Sends notifications through various channels (Telegram, Feishu/Lark webhooks)
5. Generates HTML visualizations

## Key Design Patterns

### Protocol-based Architecture

The codebase uses Python protocols and abstract base classes for extensibility:

```python
# Content sources implement ContentSource protocol
class ContentSource(Protocol):
    def fetch_articles(self, search_query: str, max_results: int = 10) -> List[Article]:
        ...

# Notifiers inherit from Notifier ABC
class Notifier(abc.ABC):
    @abc.abstractmethod
    def send(self, articles: List[Article]) -> None:
        ...

# Translators inherit from Translator ABC
class Translator(abc.ABC):
    @abc.abstractmethod
    def translate(self, text: str) -> str:
        ...
```

### Adding New Features

When adding new features, follow these patterns:

**Adding a new content source:**
1. Create a new file in `ml_subscriber/core/` (e.g., `twitter_fetcher.py`)
2. Implement the `ContentSource` protocol with `fetch_articles()` method
3. Return `Article` objects with appropriate metadata
4. Add source selection in `main.py`'s `get_fetcher_for_source()`
5. Create corresponding test file in `tests/`

**Adding a new notification channel:**
1. Create a new class inheriting from `ArticleNotifier` in `notification.py`
2. Implement the `send()` method
3. Add channel detection in `get_configured_notifiers()`
4. Add factory logic in `create_notifier()`
5. Add tests in `test_notification.py`

**Adding a new translator:**
1. Create a new class inheriting from `Translator` in `translator.py`
2. Implement the `translate()` method
3. Update `create_translator()` factory function
4. Add tests in `test_translator.py`

## Common Modification Scenarios

### Modifying Article Formatting

Notification formatting is handled in `notification.py`:
- `_format_message_html()` - HTML format for Telegram
- `_format_message_markdown_v2()` - MarkdownV2 for Telegram
- `_format_text()` - Plain text for webhooks
- `_build_feishu_post_payload()` - Rich text for Feishu/Lark

### Modifying API Interactions

- ArXiv: `arxiv_fetcher.py` - uses XML API with `requests`
- Hacker News: `hn_fetcher.py` - uses Firebase JSON API
- Telegram: `notification.py` - uses Bot API with `requests`
- DeepL: `translator.py` - uses `deepl` library
- Google Translate: `translator.py` - uses `deep_translator` library

## Testing Guidelines

### Running Tests

```bash
# Run all tests
python3 -m unittest discover tests

# Run specific test file
python3 -m unittest tests.test_notification

# Run specific test case
python3 -m unittest tests.test_notification.TestTelegramNotifier
```

### Test Patterns

Tests use `unittest.mock` to mock external dependencies:

```python
# Mock HTTP requests
@patch('ml_subscriber.core.arxiv_fetcher.requests.get')
def test_fetch_articles(self, mock_get):
    mock_get.return_value.text = MOCK_XML_RESPONSE
    ...

# Mock file I/O
@patch('builtins.open', mock_open())
def test_save_articles(self, mock_file):
    ...
```

### What to Test

1. **Fetchers**: Mock HTTP responses, test parsing logic
2. **Storage**: Mock file operations, test serialization/deserialization
3. **Notifiers**: Mock HTTP requests, test message formatting
4. **Translators**: Mock API calls, test error handling
5. **Main**: Test CLI argument parsing and command routing

## File Structure Reference

```
ml_subscriber/core/
├── models.py          # Article dataclass, ContentSource protocol
├── arxiv_fetcher.py   # ArXiv API fetcher
├── hn_fetcher.py      # Hacker News fetcher
├── storage.py         # JSON file storage
├── notification.py    # Telegram & Webhook notifiers
├── translator.py      # DeepL & Google translators
└── visualization.py   # HTML generator

tests/
├── test_arxiv_fetcher.py
├── test_hn_fetcher.py
├── test_storage.py
├── test_notification.py
├── test_translator.py
├── test_visualization.py
└── test_main.py
```

## Important Considerations

### Error Handling

- All external API calls should be wrapped in try/except
- Failed operations should log errors and return gracefully (empty list, original text)
- Never let a single article failure break the entire batch

### Security

- HTML content must be escaped (use `html.escape()`)
- URL parameters should be properly encoded
- API keys should be read from environment variables, never hardcoded

### Performance

- Use `max_results` parameter to limit API calls
- HN fetcher fetches 2x requested items to account for filtering
- Date filtering happens client-side after fetching

## CLI Reference

```bash
python3 main.py [OPTIONS]

Options:
  --fetch              Fetch articles from source
  --notify             Send notifications for stored articles
  --visualize          Generate HTML visualization
  --source {arxiv,hn}  Content source (default: arxiv)
  --days N             Fetch articles from last N days (default: 1, arxiv only)
  --max-results N      Max articles to fetch (default: 50)
  --limit N            Max articles to notify (default: 5)
  --notifier {telegram,webhook,all}  Notification channel
  --notify-style {detailed,compact}  Message verbosity
  --notify-format {text,markdown}    Output format
  --json-output PATH   JSON storage path (default: output/articles.json)
  --output PATH        HTML output path (default: output/articles.html)
  --webhook-url URL    Override WEBHOOK_URL env var
```
