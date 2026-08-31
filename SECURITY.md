# Security and privacy

Academic Clipboard is local-first and does not contain networking, telemetry, login, or cloud-sync code. Clipboard history remains on the current computer unless the user explicitly exports or copies it.

## Storage warning

The current `clipboard.db` is an unencrypted SQLite file. Anyone who can read the operating-system account's application-data directory may be able to read its contents. Do not commit, upload, or share this file.

The built-in filter skips common private keys, credentials, bearer headers, API tokens, JWTs, and labelled verification codes. This is a best-effort safety net, not a security boundary. It can miss secrets and can occasionally skip harmless text.

Pause capture before handling confidential information. Use **Clear unpinned**, or run `academic-clipboard clear --all --yes`, to remove database rows. SQLite may retain recoverable pages after deletion; for stronger removal, close the app and delete `clipboard.db` plus any `clipboard.db-wal` and `clipboard.db-shm` files from the application-data directory.

## Reporting a vulnerability

Please open a GitHub security advisory for the repository rather than posting exploitable details in a public issue. Do not include real clipboard contents, credentials, or personal data in a report.
