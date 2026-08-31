from __future__ import annotations

import re
from urllib.parse import unquote, urlparse

DOI_PATTERN = re.compile(r"(?i)(?:https?://(?:dx\.)?doi\.org/|doi:\s*)?(10\.\d{4,9}/[-._;()/:A-Z0-9]+)")


def normalize_doi(value: str) -> str:
    match = DOI_PATTERN.search(value.strip())
    if not match:
        raise ValueError("no DOI found")
    return unquote(match.group(1)).rstrip(".,;:)]}").casefold()


def doi_markdown(value: str) -> str:
    doi = normalize_doi(value)
    return f"[{doi}](https://doi.org/{doi})"


def _bibtex_parts(body: str) -> list[str]:
    parts: list[str] = []
    start = 0
    braces = 0
    quoted = False
    escaped = False
    for index, character in enumerate(body):
        if escaped:
            escaped = False
            continue
        if character == "\\":
            escaped = True
            continue
        if character == '"' and braces == 0:
            quoted = not quoted
        elif not quoted:
            if character == "{":
                braces += 1
            elif character == "}":
                braces = max(0, braces - 1)
            elif character == "," and braces == 0:
                part = body[start:index].strip()
                if part:
                    parts.append(part)
                start = index + 1
    tail = body[start:].strip()
    if tail:
        parts.append(tail)
    return parts


def format_bibtex(value: str) -> str:
    raw = value.strip()
    match = re.match(r"(?is)^@(\w+)\s*\{\s*([^,]+)\s*,(.*)\}\s*$", raw)
    if not match:
        return raw
    entry_type, key, body = match.groups()
    fields = _bibtex_parts(body)
    formatted = [f"@{entry_type.casefold()}{{{key.strip()},"]
    for field in fields:
        assignment = re.match(r"(?is)^([\w-]+)\s*=\s*(.+)$", field)
        if assignment:
            name, field_value = assignment.groups()
            formatted.append(f"  {name.casefold()} = {field_value.strip()},")
        else:
            formatted.append(f"  {field.strip()},")
    formatted.append("}")
    return "\n".join(formatted)


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


def url_markdown(value: str) -> str:
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
    return f"[{title}]({url})"
