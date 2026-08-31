from __future__ import annotations

import re
from urllib.parse import urlparse

from academic_clipboard.formatters import (
    DOI_PATTERN,
    doi_markdown,
    fenced_code,
    format_bibtex,
    markdown_note,
    normalize_doi,
    url_markdown,
)
from academic_clipboard.models import ClassifiedClip

URL_PATTERN = re.compile(r"(?i)^https?://[^\s]+$")
BIBTEX_PATTERN = re.compile(
    r"(?is)^@(?:article|book|inproceedings|misc|phdthesis|mastersthesis|techreport|online)\s*\{"
)


def _url_subtype(value: str) -> str:
    parsed = urlparse(value)
    host = parsed.netloc.casefold().removeprefix("www.")
    path = parsed.path.casefold()
    if host == "github.com" or host.endswith("gitlab.com"):
        return "github"
    if any(
        name in host
        for name in ("doi.org", "arxiv.org", "pubmed.ncbi.nlm.nih.gov", "ssrn.com", "openalex.org")
    ):
        return "paper"
    if any(name in host for name in ("zenodo.org", "figshare.com", "kaggle.com", "dataverse", "data.")):
        return "dataset"
    if "docs" in host or "readthedocs" in host or "/docs" in path or host.startswith("developer."):
        return "docs"
    return "web"


def _code_language(value: str) -> str:
    stripped = value.strip()
    fenced = re.match(r"^```([\w+-]*)", stripped)
    if fenced:
        return fenced.group(1) or "text"
    tests = (
        ("python", r"(?m)^\s*(?:from\s+\w+\s+import|import\s+\w+|def\s+\w+\s*\(|class\s+\w+\s*[:(])"),
        ("javascript", r"(?m)^\s*(?:const|let|var|function|import|export)\b|=>"),
        ("sql", r"(?is)^\s*(?:select|insert|update|delete|create\s+table)\b"),
        ("shell", r"(?m)^\s*(?:#!/.*(?:sh|bash)|(?:git|npm|pip|python|docker)\s+)"),
        ("json", r"(?s)^\s*[\[{].*[\]}]\s*$"),
    )
    for language, pattern in tests:
        if re.search(pattern, stripped):
            return language
    return "text"


def _looks_like_code(value: str) -> bool:
    if value.strip().startswith("```"):
        return True
    if "\n" not in value:
        return False
    signals = sum(
        bool(re.search(pattern, value, re.MULTILINE))
        for pattern in (
            r"^\s*(?:def|class|function|const|let|var|import|from|SELECT|CREATE)\b",
            r"[{};]\s*$",
            r"(?:=>|==|!=|<=|>=|::)",
            r"^\s{2,}\S+",
        )
    )
    return signals >= 2


def _looks_like_title(value: str) -> bool:
    if "\n" in value or value.endswith((".", "?", "!", "。", "？", "！")):
        return False
    words = re.findall(r"[\w\u3400-\u9fff'-]+", value, re.UNICODE)
    return 4 <= len(words) <= 30 and 20 <= len(value) <= 240


def classify(value: str) -> ClassifiedClip:
    content = value.strip()
    if not content:
        return ClassifiedClip("text", "empty", "Empty text", "")
    doi_match = DOI_PATTERN.fullmatch(content) or (
        DOI_PATTERN.search(content) if len(content) <= 180 else None
    )
    if doi_match:
        doi = normalize_doi(content)
        return ClassifiedClip("doi", "paper", doi, doi_markdown(doi))
    if BIBTEX_PATTERN.match(content):
        first = re.search(r"(?i)^@\w+\s*\{\s*([^,]+)", content)
        key = first.group(1).strip() if first else "BibTeX entry"
        return ClassifiedClip("bibtex", "citation", key, format_bibtex(content))
    if URL_PATTERN.match(content):
        subtype = _url_subtype(content)
        parsed = urlparse(content)
        title = parsed.netloc.removeprefix("www.") + (parsed.path.rstrip("/") or "")
        return ClassifiedClip("url", subtype, title, url_markdown(content))
    if _looks_like_code(content):
        language = _code_language(content)
        raw = re.sub(r"(?s)^```[\w+-]*\s*|\s*```$", "", content).strip("\n")
        first_line = next((line.strip() for line in raw.splitlines() if line.strip()), "Code snippet")
        return ClassifiedClip("code", language, first_line[:100], fenced_code(raw, language))
    if _looks_like_title(content):
        clean = " ".join(content.split())
        return ClassifiedClip("title", "paper-title", clean, markdown_note(clean))
    preview = " ".join(content.split())[:100]
    return ClassifiedClip("text", "plain", preview, content)
