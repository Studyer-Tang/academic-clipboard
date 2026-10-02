from __future__ import annotations

import re
from urllib.parse import quote, unquote, urlparse

from academic_clipboard.bibtex import parse_bibtex

DOI_PATTERN = re.compile(
    r"(?i)(?:https?://(?:dx\.)?doi\.org/|doi:\s*)?(10\.\d{4,9}/[-._;()/:A-Z0-9\[\]{}+%]+)"
)


def normalize_doi(value: str) -> str:
    match = DOI_PATTERN.search(value.strip())
    if not match:
        raise ValueError("no DOI found")
    doi = unquote(match.group(1))
    while doi:
        if doi[-1] in ".,;:":
            doi = doi[:-1]
        elif doi[-1] in ")]}":
            closer = doi[-1]
            opener = {")": "(", "]": "[", "}": "{"}[closer]
            if doi.count(closer) <= doi.count(opener):
                break
            doi = doi[:-1]
        else:
            break
    return doi.casefold()


def doi_url(value: str) -> str:
    return "https://doi.org/" + quote(normalize_doi(value), safe="/:._-;")


def doi_markdown(value: str) -> str:
    doi = normalize_doi(value)
    label = re.sub(r"([\\\[\]])", r"\\\1", doi)
    return f"[{label}]({doi_url(value)})"


def doi_latex(value: str) -> str:
    doi = normalize_doi(value)
    target = doi_url(value).replace("%", r"\%")
    label = re.sub(r"([%#&_{}])", r"\\\1", doi)
    return rf"\href{{{target}}}{{{label}}}"


def format_bibtex(value: str) -> str:
    raw = value.strip()
    entries = parse_bibtex(raw)
    if entries is None:
        return raw
    formatted = []
    for entry in entries:
        lines = [f"@{entry.entry_type}{{{entry.key},"]
        lines.extend(f"  {name} = {field_value}," for name, field_value in entry.fields)
        lines.append("}")
        formatted.append("\n".join(lines))
    return "\n\n".join(formatted)


def markdown_note(title: str) -> str:
    clean = " ".join(title.split())
    return (
        f"# {clean}\n\n"
        "- DOI: \n"
        "- Authors: \n"
        "- Year: \n"
        "- Status: to-read\n\n"
        "## Summary\n\n"
        "## Key claims\n\n"
        "## Notes\n"
    )


def fenced_code(value: str, language: str = "text") -> str:
    code = value.strip("\n")
    fence = "````" if "```" in code else "```"
    return f"{fence}{language}\n{code}\n{fence}"


def url_title(value: str) -> str:
    url = value.strip()
    parsed = urlparse(url)
    host = parsed.netloc.removeprefix("www.")
    path = unquote(parsed.path).strip("/")
    if host.casefold() == "github.com" and path:
        label = path.split("/")[:2]
        title = " / ".join(label)
    elif path:
        title = path.split("/")[-1].replace("-", " ").replace("_", " ").strip() or host
    else:
        title = host
    return title


def url_markdown(value: str) -> str:
    url = value.strip()
    title = re.sub(r"([\\\[\]])", r"\\\1", url_title(url))
    target = quote(url, safe="/:?&=#%+;,@!~*'._-")
    return f"[{title}]({target})"
