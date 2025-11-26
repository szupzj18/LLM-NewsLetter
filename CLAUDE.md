# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## High-level code architecture and structure

This project is a Python application for subscribing to and tracking the latest information in the machine learning (ML) and deep learning (DL) fields. The current version fetches the latest research papers from ArXiv and saves them as a structured JSON file.

The core logic is organized into two main components:

-   `ml_subscriber/core/arxiv_fetcher.py`: This module is responsible for fetching and parsing articles from the ArXiv API. The `ArxivFetcher` class handles the API requests and parses the XML response into a list of `Article` objects.
-   `ml_subscriber/core/storage.py`: This module handles the storage of articles. The `JsonStorage` class saves a list of `Article` objects to a JSON file and can load them back.

The main entry point of the application is `main.py`, which demonstrates how to use `ArxivFetcher` and `JsonStorage` to fetch articles and save them.

The project uses the standard Python `unittest` framework for testing. Tests are located in the `tests/` directory and mock external dependencies like network requests and file I/O.

## Common development tasks

### Running the application

To run the application, execute the `main.py` script:

```bash
python3 main.py
```

### Running tests

To run the full test suite, use the following command:

```bash
python3 -m unittest discover tests
```
