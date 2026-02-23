# AGENTS.md

Instructions for AI agents working with this codebase. For project facts (module descriptions, commands, env vars), see `CLAUDE.md`.

---

## Rules

These are mandatory rules. Always follow them when modifying this codebase.

### R1: Error Handling

- MUST wrap all external API calls in try/except.
- MUST return gracefully on failure (empty list for fetchers, original text for translators).
- MUST NOT let a single item failure break the entire batch.

### R2: Security

- MUST escape all user-provided content before rendering in HTML (`html.escape()`).
- MUST properly encode URLs.
- MUST read API keys from environment variables. NEVER hardcode secrets.

### R3: Testing

- MUST add or update tests in the corresponding `tests/test_<module>.py` when modifying a core module.
- MUST mock external dependencies (HTTP requests, file I/O) using `unittest.mock`.
- MUST run `python3 -m unittest discover tests` and ensure all tests pass before considering a task complete.

### R4: Documentation Sync

- MUST update this file (Agents.md) when:
  - Adding, removing, or renaming a core module — update Patterns and References sections.
  - Changing an extension pattern (new ABC, protocol, or factory) — update Patterns section.
  - Changing error handling, security, or testing conventions — update Rules section.
- MUST update `CLAUDE.md` when:
  - Adding or removing a core module — update the "Core Modules" section.
  - Changing CLI commands or environment variables — update the corresponding sections.
- MUST NOT duplicate content between `CLAUDE.md` and this file.

### R5: Performance

- MUST use `max_results` parameter to limit API calls.
- SHOULD perform filtering client-side after fetching — fetch broadly, filter locally.

---

## Patterns

Follow these patterns when extending the project. Each pattern describes the steps and the contract to satisfy.

### P1: Adding a New Content Source

Contract: implement the `ContentSource` protocol defined in `models.py`.

1. Create a new file in `ml_subscriber/core/` (e.g., `reddit_fetcher.py`).
2. Implement `fetch_articles(search_query, max_results) -> List[Article]`.
3. Map source data to `Article` objects. Set `metadata["source"]` to a unique identifier.
4. Register the source in `main.py` — search for `get_fetcher_for_source()`.
5. Create `tests/test_<source>_fetcher.py` with mocked HTTP responses.

### P2: Adding a New Notification Channel

Contract: inherit from `ArticleNotifier` in `notification.py`.

1. Create a new class inheriting from `ArticleNotifier`.
2. Implement the `send(articles)` method.
3. Register it in `main.py` — search for `get_configured_notifiers()` and `create_notifier()`.
4. Add tests in `tests/test_notification.py`.

### P3: Adding a New Translator

Contract: inherit from `Translator` in `translator.py`.

1. Create a new class inheriting from `Translator`.
2. Implement the `translate(text) -> str` method.
3. Update `create_translator()` factory function in the same file.
4. Add tests in `tests/test_translator.py`.

### P4: Testing Pattern

All tests follow the same structure — mock the external boundary, test the logic:

```python
@patch('ml_subscriber.core.<module>.requests.get')
def test_something(self, mock_get):
    mock_get.return_value.text = MOCK_RESPONSE
    # call the method under test
    # assert on the parsed/formatted result
```

---

## References

Quick lookup table. When in doubt, read the source file directly rather than relying on specific names listed here.

| Want to change...       | Look in...                                           | How to find it                                                  |
| ----------------------- | ---------------------------------------------------- | --------------------------------------------------------------- |
| Article data model      | `models.py`                                          | `Article` dataclass                                             |
| Notification formatting | `notification.py`                                    | Search for `_format_` prefix                                    |
| CLI arguments           | `main.py`                                            | Search for `parse_args()`, or run `python3 main.py --help`      |
| External API calls      | The fetcher or notifier file for that source/channel | Each owns its own HTTP logic                                    |
| Translation config      | `translator.py`                                      | Search for `create_translator()`                                |
| Notifier wiring         | `main.py`                                            | Search for `create_notifier()` and `get_configured_notifiers()` |
