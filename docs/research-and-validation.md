# Research and validation — 0.5

Reviewed 2026-10-01. This is a small qualitative review of established workflows and first-hand requests, not a representative survey of all researchers.

| Evidence | Product decision |
| --- | --- |
| [Zotero Quick Copy](https://www.zotero.org/support/creating_bibliographies) supports copying citations and bibliographies into writing tools. [Import from Clipboard](https://www.zotero.org/support/kb/import_from_clipboard) accepts BibTeX/RIS/CSL JSON. | Keep raw BibTeX and export `.bib` for Zotero; do not invent missing reference metadata or attempt to replace a citation manager. |
| [Zotero annotation templates](https://www.zotero.org/support/note_templates) retain annotation text, citations and comments. | Offer “Quote with source” using the source and page/section explicitly entered by the reader. |
| [PDF formatting discussion](https://forums.zotero.org/discussion/101992/retain-formatting-when-copying-from-zotero-pdf-reader) reports loss of line structure, including code. | PDF prose cleanup is an explicit copy action, never an automatic edit. Preserve blank-line paragraphs; provide a separate, review-required dehyphenation action. Do not offer prose cleanup on classified code/tables. |
| [NSPasteboard conventions](https://nspasteboard.org/) identify confidential and temporary clipboard payloads. | Respect these markers before storage, including manual capture; a password-pattern heuristic alone is insufficient. |

No network requests, account, AI model or telemetry were added to the application. Local snippets remain usable offline. OCR, cloud synchronization and online DOI enrichment are deferred because they add weight, privacy choices and metadata failure modes beyond this release's purpose.

## Offline conversion boundaries

BibTeX normalization now processes complete records separately and preserves nested braces, quoted values, escape sequences and field expressions. Both brace and parenthesis record delimiters are accepted. A malformed record or unsupported `@string`, `@comment`, `@preamble`, outside comment or trailing text causes the whole snippet to remain unchanged; the app does not salvage a partial bibliography. Reference drafts are offered only when every record has unambiguous literal fields. Macros, concatenation and duplicate fields keep their BibTeX copy action but receive no APA/GB/T draft action. Missing metadata is still visibly marked; author-name conventions, LaTeX commands and full citation-style conformance still require review. The stored original and `.bib` export remain untouched.

Chinese title detection uses character length, research terms and sentence punctuation rather than whitespace word counts. It is a conservative heuristic: short or unconventional titles may remain text, and a long unpunctuated research sentence can still resemble a title. No model or online classification is used.

DOI copy actions retain balanced suffix parentheses/brackets/braces and remove excess closing delimiters from surrounding prose. Links encode the destination and escape markup delimiters. Normalization still treats trailing `.`, `,`, `;` and `:` as prose punctuation; unusual DOI suffixes with those endings need an original-text check. Synthetic examples test string handling only and do not claim that a DOI is registered or that an online destination resolves.

## Repeatable checks

```sh
python -m unittest discover -s tests -v
ruff check .
ruff format --check .
python scripts/benchmark.py
python scripts/smoke_desktop.py
python scripts/build_release.py
```

The desktop smoke test uses temporary synthetic history, pauses capture before the event loop starts, checks tray and hotkey registration, both window sizes and search, then exits. Native macOS pasteboard tests use a private named pasteboard, never the user's clipboard. The release build launches the **packaged binary**, checks its JSON test report, then creates the download and SHA-256 checksum.

### Local measurements

Apple Silicon, macOS, Python 3.13.15 / Tk 9.0.4; one local run, not a guarantee for other machines:

| Check | Result |
| --- | --- |
| Synthetic history: 500 clips, ~96,000 characters per clip; old full-row query | 170.09 ms; 95.851 MiB peak Python allocations |
| Same history, bounded preview query | 18.21 ms; 0.491 MiB peak Python allocations |
| Search one clip in that history | 64.95 ms |
| Packaged desktop smoke initialization | ~0.32 s (after Python imports; excludes cold process startup) |
| Local arm64 DMG / installed `.app` | ~20 MiB / ~42 MiB; CI builds may differ |

The allocation measurement is **not total application RAM**. Cocoa/Tk/Python and graphics buffers also consume memory. A paused GUI with three synthetic clips showed ~191 MiB RSS locally, including shared frameworks. macOS `vmmap -summary` reported 81.5 MiB physical footprint (86.3 MiB peak) for the updated app; screenshots can increase peaks. Size limits and preview loading prevent history size from directly becoming resident full-text history.

The owner additionally verified Control+Option+V brings up the app while another application is foreground on their Mac. Global key registration is automated; other physical keyboard layouts/reserved system shortcuts and first launch under Gatekeeper still need real-device acceptance. Windows and Intel macOS package checks run in CI; they do not cover every hardware/OS combination. Releases are unsigned previews, without Developer ID notarization or a Windows publisher certificate.
