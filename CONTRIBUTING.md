# Contributing

Contributions are welcome. Keep the core local-first, dependency-light, and understandable without a cloud account.

1. Create a focused branch.
2. Install the editable development package with `python -m pip install -e ".[dev]"`.
3. Add or update tests for behavior changes.
4. Run `python -m unittest discover -s tests -v`, `ruff format --check .`, and `ruff check .`.
5. Explain user-visible behavior and privacy implications in the pull request.

Never add real clipboard databases, exports, credentials, access tokens, or personal research material to fixtures. Use obviously synthetic values in tests.
