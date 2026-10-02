"""Conservative offline parsing for copy actions, not a BibTeX engine.

Accept complete records and preserve their field expressions. Unsupported
directives, comments or malformed input must stay as original text. In
particular, citation drafts never resolve string macros or concatenation.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_HEADER = re.compile(r"@([A-Za-z][\w-]*)\s*([{(])\s*([^\s,{}()]+)\s*")
_ASSIGNMENT = re.compile(r"([\w-]+)\s*=\s*")
_ATOM = re.compile(r'[^\s,#{}"()%]+')


@dataclass(frozen=True, slots=True)
class BibtexEntry:
    entry_type: str
    key: str
    fields: tuple[tuple[str, str], ...]


def _skip_space(value: str, position: int) -> int:
    while position < len(value) and value[position].isspace():
        position += 1
    return position


def _atom_end(value: str, position: int) -> int | None:
    if position >= len(value):
        return None
    opener = value[position]
    if opener not in {"{", '"'}:
        atom = _ATOM.match(value, position)
        return atom.end() if atom else None
    braces = 1 if opener == "{" else 0
    escaped = False
    for index in range(position + 1, len(value)):
        character = value[index]
        if escaped:
            escaped = False
        elif character == "\\":
            escaped = True
        elif character == "{":
            braces += 1
        elif character == "}":
            braces -= 1
            if braces < 0:
                return None
            if braces == 0 and opener == "{":
                return index + 1
        elif character == '"' and opener == '"' and braces == 0:
            return index + 1
    return None


def _expression_end(value: str, position: int) -> int | None:
    end = _atom_end(value, position)
    while end is not None:
        following = _skip_space(value, end)
        if following >= len(value) or value[following] != "#":
            return end
        end = _atom_end(value, _skip_space(value, following + 1))
    return None


def parse_bibtex(value: str) -> list[BibtexEntry] | None:
    """Parse the whole snippet, or reject it without extracting partial records."""
    position = _skip_space(value, 0)
    entries: list[BibtexEntry] = []
    while position < len(value):
        header = _HEADER.match(value, position)
        if not header or header.group(1).casefold() in {"comment", "preamble", "string"}:
            return None
        entry_type, opener, key = header.groups()
        closer = "}" if opener == "{" else ")"
        position = header.end()
        fields: list[tuple[str, str]] = []
        if position < len(value) and value[position] == ",":
            position = _skip_space(value, position + 1)
            while position < len(value) and value[position] != closer:
                assignment = _ASSIGNMENT.match(value, position)
                if not assignment:
                    return None
                name = assignment.group(1).casefold()
                position = assignment.end()
                end = _expression_end(value, position)
                if end is None:
                    return None
                fields.append((name, value[position:end]))
                position = _skip_space(value, end)
                if position < len(value) and value[position] == ",":
                    position = _skip_space(value, position + 1)
                elif position >= len(value) or value[position] != closer:
                    return None
        if position >= len(value) or value[position] != closer:
            return None
        entries.append(BibtexEntry(entry_type.casefold(), key, tuple(fields)))
        position = _skip_space(value, position + 1)
    return entries or None


def literal_fields(entry: BibtexEntry) -> dict[str, str] | None:
    """Only unambiguous literal metadata may be used in a reference draft."""
    fields = {"key": entry.key}
    for name, value in entry.fields:
        if name in fields or _atom_end(value, 0) != len(value):
            return None
        if value.startswith(("{", '"')):
            clean = re.sub(r"[{}]", "", value[1:-1]).strip()
        elif re.fullmatch(r"[0-9]+", value):
            clean = value
        else:
            return None
        fields[name] = clean
    return fields
