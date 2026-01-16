# Verity Test Suite

This directory contains the unit and integration tests for the Verity application. The tests are built using `pytest` and are structured to mirror the codebase organisation.

## Structure

- **`tests/app/`**: Tests for the Dash frontend logic (callbacks, layout).
- **`tests/data/`**: Tests for the backend logic (queries, models, plots, utils).
- **`tests/conftest.py`**: Shared fixtures (in-memory database session) for testing.

## Dependencies

The test suite requires `pytest`. If it is not already installed in your environment, install it via pip:

```bash
pip install pytest
```

## Running Tests

Ensure you are in the project root directory (`eggd_verity/`) before running tests to ensure python module paths are resolved correctly.

**Run all tests:**
```bash
pytest
```

**Run a specific module:**
```bash
pytest tests/data/queries/
```

**Run with verbose output:**
```bash
pytest -v
```

## Fixtures

The `session` fixture defined in `conftest.py` provides an isolated in-memory SQLite database for each test function. This ensures that database interactions (inserts, queries) are fast and do not persist or interfere with other tests.