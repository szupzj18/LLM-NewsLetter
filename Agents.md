# Agents.md

This document provides guidance for AI agents working with this codebase. For project overview, module descriptions, environment variables, and common commands, see `CLAUDE.md`.

## Key Design Patterns

### Protocol-based Architecture

The codebase uses Python protocols and abstract base classes for extensibility. All extension points follow the same shape:

```python
# Content sources implement ContentSource protocol (models.py)
class ContentSource(Protocol):
    def fetch_articles(self, search_query: str, max_results: int = 10) -> List[Article]: ...

# Notifiers inherit from Notifier ABC (notification.py)
class Notifier(abc.ABC):
    @abc.abstractmethod
    def send(self, articles: List[Article]) -> None: ...

# Translators inherit from Translator ABC (translator.py)
class Translator(abc.ABC):
    @abc.abstractmethod
    def translate(self, text: str) -> str: ...
```

### Unified Data Model

All content sources map their data to the same `Article` dataclass. Source-specific information is stored in the `metadata` dict field (e.g., `metadata["source"]` identifies the origin).

### Factory Functions

Configuration-dependent object creation uses factory functions (e.g., `create_translator()` in `translator.py`). Follow this pattern when adding new configurable components.

## How to Extend the Project

### Adding a new content source

1. Create a new file in `ml_subscriber/core/` implementing `ContentSource` protocol
2. Map source data to `Article` objects, setting `metadata["source"]` to identify the origin
3. Register the new source in `main.py` — look for `get_fetcher_for_source()`
4. Create a corresponding test file in `tests/`

### Adding a new notification channel

1. Create a new class inheriting from `ArticleNotifier` in `notification.py`
2. Implement the `send()` method
3. Register it in `main.py` — look for `get_configured_notifiers()` and `create_notifier()`
4. Add tests in `test_notification.py`

### Adding a new translator

1. Create a new class inheriting from `Translator` in `translator.py`
2. Implement the `translate()` method
3. Update the `create_translator()` factory function in the same file
4. Add tests in `test_translator.py`

## Where to Find Things

| Want to change... | Look in... | Hint |
|---|---|---|
| Notification message formatting | `notification.py` | Search for methods prefixed with `_format_` |
| External API calls | The corresponding fetcher or notifier file | Each source/channel owns its own HTTP logic |
| CLI arguments | `main.py` | See `parse_args()`, or run `python3 main.py --help` |
| Data model fields | `models.py` | `Article` dataclass |

## Testing Conventions

Tests use `unittest` with `unittest.mock` to isolate external dependencies:

```python
# Typical pattern: mock the HTTP layer, test parsing/formatting logic
@patch('ml_subscriber.core.arxiv_fetcher.requests.get')
def test_fetch_articles(self, mock_get):
    mock_get.return_value.text = MOCK_XML_RESPONSE
    ...
```

Each core module has a corresponding `tests/test_<module>.py` file. When adding or modifying a module, update its test file accordingly.

## Coding Rules

### Error Handling

- All external API calls must be wrapped in try/except
- Failed operations should log errors and return gracefully (empty list, original text)
- Never let a single article failure break the entire batch

### Security

- HTML content must be escaped (`html.escape()`)
- URL parameters should be properly encoded
- API keys must come from environment variables, never hardcoded

### Performance

- Use `max_results` to limit API calls
- Date filtering happens client-side after fetching — fetch broadly, filter locally
