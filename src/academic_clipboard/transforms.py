from __future__ import annotations

import html
import re
from dataclasses import dataclass

from academic_clipboard.formatters import (
    doi_markdown,
    format_bibtex,
    markdown_note,
    normalize_doi,
    url_markdown,
)
from academic_clipboard.i18n import tr
from academic_clipboard.models import ClipboardItem


@dataclass(frozen=True, slots=True)
class ContentTransform:
    key: str
    label: str
    value: str


def clean_pdf_text(value: str, dehyphenate: bool = False) -> str:
    """Opt-in prose cleanup; never replace the saved original or infer paragraph boundaries."""
    text = value.replace("\r\n", "\n").replace("\r", "\n").replace("\u00ad", "")
    for glyph, letters in (("ﬀ", "ff"), ("ﬁ", "fi"), ("ﬂ", "fl"), ("ﬃ", "ffi"), ("ﬄ", "ffl")):
        text = text.replace(glyph, letters)
    if dehyphenate:
        text = re.sub(r"([A-Za-z]{2,})-[ \t]*\n[ \t]*(?=[a-z])", r"\1", text)
    paragraphs = re.split(r"\n[ \t]*\n+", text.strip())
    result = []
    for paragraph in paragraphs:
        paragraph = re.sub(r"(?<=[\u3400-\u9fff])[ \t]*\n[ \t]*(?=[\u3400-\u9fff])", "", paragraph)
        result.append(re.sub(r"[\s\u00a0]+", " ", paragraph).strip())
    return "\n\n".join(result)


def quote_with_source(item: ClipboardItem) -> str:
    quote = "\n".join("> " + line if line else ">" for line in item.content.splitlines())
    attribution = " · ".join(part for part in (item.source, item.locator) if part)
    return quote + (f"\n\n— {attribution}" if attribution else "")


def _clean_bibtex_value(value: str) -> str:
    value = value.strip().rstrip(",").strip()
    if len(value) >= 2 and ((value[0], value[-1]) in {("{", "}"), ('"', '"')}):
        value = value[1:-1]
    return re.sub(r"[{}]", "", value).strip()


def bibtex_fields(value: str) -> dict[str, str]:
    match = re.match(r"(?is)^@\w+\s*\{\s*([^,]+)\s*,(.*)\}\s*$", value.strip())
    if not match:
        return {}
    fields: dict[str, str] = {"key": match.group(1).strip()}
    body = match.group(2)
    start = 0
    braces = 0
    quoted = False
    escaped = False
    parts: list[str] = []
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
                parts.append(body[start:index])
                start = index + 1
    parts.append(body[start:])
    for part in parts:
        assignment = re.match(r"(?is)^\s*([\w-]+)\s*=\s*(.+?)\s*$", part)
        if assignment:
            fields[assignment.group(1).casefold()] = _clean_bibtex_value(assignment.group(2))
    return fields


def _authors(value: str) -> list[str]:
    return [author.strip() for author in re.split(r"\s+and\s+", value, flags=re.IGNORECASE) if author.strip()]


def bibtex_reference(value: str, style: str) -> str:
    fields = bibtex_fields(value)
    if not fields:
        return value.strip()
    authors = _authors(fields.get("author", ""))
    author_text = ", ".join(authors) if authors else tr("佚名", "Anonymous")
    title = fields.get("title", tr("未命名文献", "Untitled work"))
    year = fields.get("year", "n.d.")
    venue = fields.get("journal") or fields.get("booktitle") or fields.get("publisher", "")
    volume = fields.get("volume", "")
    number = fields.get("number", "")
    pages = fields.get("pages", "").replace("--", "–")
    doi = fields.get("doi", "")
    if style == "gbt":
        issue = f"{volume}({number})" if volume and number else volume or (f"({number})" if number else "")
        publication = ", ".join(part for part in (year, issue) if part)
        if pages:
            publication = f"{publication}: {pages}" if publication else pages
        result = f"{author_text}. {title}[J]."
        if venue:
            result += f" {venue}"
        if publication:
            result += f", {publication}"
        result += "."
        if doi:
            result += f" DOI: {doi}."
        return result
    issue = f"({number})" if number else ""
    journal = f" {venue}, {volume}{issue}" if venue else ""
    page_text = f", {pages}" if pages else ""
    doi_text = f". https://doi.org/{doi}" if doi else ""
    return f"{author_text} ({year}). {title}.{journal}{page_text}{doi_text}".strip()


def table_rows(value: str) -> list[list[str]]:
    lines = [line.strip() for line in value.strip().splitlines() if line.strip()]
    if not lines:
        return []
    if all("\t" in line for line in lines):
        return [[cell.strip() for cell in line.split("\t")] for line in lines]
    if all("|" in line for line in lines):
        rows = [[cell.strip() for cell in line.strip("|").split("|")] for line in lines]
        return [row for row in rows if not all(re.fullmatch(r":?-{3,}:?", cell) for cell in row)]
    return []


def markdown_table(value: str) -> str:
    rows = table_rows(value)
    if not rows:
        return value.strip()
    width = max(len(row) for row in rows)
    padded = [row + [""] * (width - len(row)) for row in rows]
    escaped = [[cell.replace("|", "\\|") for cell in row] for row in padded]
    header = escaped[0]
    body = escaped[1:]
    lines = ["| " + " | ".join(header) + " |", "| " + " | ".join("---" for _ in header) + " |"]
    lines.extend("| " + " | ".join(row) + " |" for row in body)
    return "\n".join(lines)


def latex_table(value: str) -> str:
    rows = table_rows(value)
    if not rows:
        return value.strip()
    width = max(len(row) for row in rows)

    def escape(cell: str) -> str:
        replacements = {
            "&": r"\&",
            "%": r"\%",
            "#": r"\#",
            "_": r"\_",
            "$": r"\$",
            "{": r"\{",
            "}": r"\}",
            "\\": r"\textbackslash{}",
            "~": r"\textasciitilde{}",
            "^": r"\textasciicircum{}",
        }
        return "".join(replacements.get(character, character) for character in cell)

    padded = [row + [""] * (width - len(row)) for row in rows]
    lines = [f"\\begin{{tabular}}{{{'l' * width}}}", "\\hline"]
    for index, row in enumerate(padded):
        lines.append(" & ".join(escape(cell) for cell in row) + r" \\")
        if index == 0:
            lines.append("\\hline")
    lines.extend(["\\hline", "\\end{tabular}"])
    return "\n".join(lines)


def available_transforms(item: ClipboardItem) -> list[ContentTransform]:
    transforms = [ContentTransform("original", tr("复制原文", "Copy original"), item.content)]
    if item.kind == "image":
        return transforms
    if item.source or item.locator:
        transforms.append(
            ContentTransform("source-quote", tr("带出处复制", "Quote with source"), quote_with_source(item))
        )
    if item.kind in {"text", "title"} and "\n" in item.content:
        transforms.extend(
            (
                ContentTransform(
                    "pdf-text", tr("合并 PDF 断行", "Join PDF lines"), clean_pdf_text(item.content)
                ),
                ContentTransform(
                    "pdf-dehyphenate",
                    tr("合并断行及连字符（需核对）", "Join lines + hyphens (review)"),
                    clean_pdf_text(item.content, dehyphenate=True),
                ),
            )
        )
    if item.kind == "doi":
        doi = normalize_doi(item.content)
        transforms.extend(
            (
                ContentTransform("doi-url", tr("DOI 链接", "DOI URL"), f"https://doi.org/{doi}"),
                ContentTransform("markdown", "Markdown", doi_markdown(doi)),
                ContentTransform("latex", "LaTeX", rf"\href{{https://doi.org/{doi}}}{{{doi}}}"),
            )
        )
    elif item.kind == "bibtex":
        transforms.extend(
            (
                ContentTransform("bibtex", tr("规范 BibTeX", "Clean BibTeX"), format_bibtex(item.content)),
                ContentTransform(
                    "gbt", tr("GB/T 7714 草稿", "GB/T 7714 draft"), bibtex_reference(item.content, "gbt")
                ),
                ContentTransform("apa", tr("APA 草稿", "APA draft"), bibtex_reference(item.content, "apa")),
            )
        )
    elif item.kind == "url":
        markdown = url_markdown(item.content)
        label = markdown.removeprefix("[").split("](", 1)[0]
        transforms.extend(
            (
                ContentTransform("markdown", "Markdown", markdown),
                ContentTransform(
                    "html",
                    "HTML",
                    f'<a href="{html.escape(item.content, quote=True)}">{html.escape(label)}</a>',
                ),
            )
        )
    elif item.kind == "title":
        transforms.extend(
            (
                ContentTransform(
                    "heading", tr("Markdown 标题", "Markdown heading"), f"# {item.content.strip()}"
                ),
                ContentTransform(
                    "note", tr("阅读笔记模板", "Reading-note template"), markdown_note(item.content)
                ),
            )
        )
    elif item.kind == "code":
        transforms.append(ContentTransform("fenced", tr("代码块", "Fenced code"), item.normalized_content))
    elif item.kind == "table":
        transforms.extend(
            (
                ContentTransform(
                    "markdown-table", tr("Markdown 表格", "Markdown table"), markdown_table(item.content)
                ),
                ContentTransform("latex-table", tr("LaTeX 表格", "LaTeX table"), latex_table(item.content)),
                ContentTransform(
                    "tsv-table",
                    tr("Excel / Word 制表符表格", "Excel / Word tab-separated table"),
                    "\n".join("\t".join(row) for row in table_rows(item.content)),
                ),
            )
        )
    elif item.kind == "formula":
        formula = item.content.strip()
        for start, end in ((r"\[", r"\]"), (r"\(", r"\)"), ("$$", "$$"), ("$", "$")):
            if formula.startswith(start) and formula.endswith(end):
                formula = formula[len(start) : -len(end)].strip()
                break
        transforms.extend(
            (
                ContentTransform("inline-latex", tr("行内公式", "Inline LaTeX"), rf"\({formula}\)"),
                ContentTransform("display-latex", tr("独立公式", "Display LaTeX"), f"\\[\n{formula}\n\\]"),
            )
        )
    else:
        quote = "\n".join(f"> {line}" if line else ">" for line in item.content.splitlines())
        transforms.append(ContentTransform("quote", tr("Markdown 引文", "Markdown quote"), quote))
    return transforms
