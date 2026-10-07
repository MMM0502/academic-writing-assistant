from __future__ import annotations

from dataclasses import dataclass, asdict
import re
from typing import Iterable

from .parsers import iter_reference_lines, split_paragraphs, title_from_text


STYLE_LABELS = {
    "gb7714": "GB/T 7714-2015",
    "apa7": "APA 7",
    "ieee": "IEEE",
}


@dataclass
class Reference:
    index: int
    raw: str
    authors: str
    year: str
    title: str
    source: str
    formatted: str
    duplicate: bool = False


def _normalize_spaces(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("．", ".").strip(" \t.;；。"))


def parse_reference(raw: str, index: int, style: str) -> Reference:
    line = re.sub(r"^\s*(?:\[\d+\]|\d+[.)、])\s*", "", raw)
    line = _normalize_spaces(line)
    year_match = re.search(r"\b(19|20)\d{2}\b", line)
    year = year_match.group(0) if year_match else "n.d."
    parts = [part.strip() for part in re.split(r"[。.!?]\s+", line, maxsplit=2) if part.strip()]
    authors = parts[0] if parts else "未知作者"
    title = parts[1] if len(parts) > 1 else line
    source = parts[2] if len(parts) > 2 else ""
    if source and year != "n.d.":
        source = re.sub(rf"[,，]?\s*{re.escape(year)}\s*$", "", source).strip(" ,，")
    if style == "apa7":
        formatted = f"{authors} ({year}). {title}."
        if source:
            formatted += f" {source}."
    elif style == "ieee":
        formatted = f"[{index}] {authors}, \"{title},\""
        if source:
            formatted += f" {source},"
        formatted += f" {year}."
    else:
        formatted = f"{index}. {authors}. {title}"
        if source:
            formatted += f". {source}"
        formatted += f", {year}."
    return Reference(index, raw, authors, year, title, source, formatted)


def format_references(text: str, style: str = "gb7714") -> tuple[list[Reference], list[str]]:
    if style not in STYLE_LABELS:
        raise ValueError("不支持的参考文献格式。")
    lines = list(iter_reference_lines(text))
    if not lines:
        # Also accept a document consisting only of reference-like lines.
        lines = [paragraph for paragraph in split_paragraphs(text) if re.search(r"\b(?:19|20)\d{2}\b", paragraph)]
    references = [parse_reference(line, index, style) for index, line in enumerate(lines, start=1)]
    warnings: list[str] = []
    seen: dict[str, int] = {}
    for reference in references:
        key = re.sub(r"[^a-z0-9\u4e00-\u9fff]", "", reference.title.lower())
        if key and key in seen:
            reference.duplicate = True
            warnings.append(f"第 {reference.index} 条与第 {seen[key]} 条疑似重复。")
        elif key:
            seen[key] = reference.index
        if reference.year == "n.d.":
            warnings.append(f"第 {reference.index} 条未识别出出版年份。")
    if not references:
        warnings.append("未识别到参考文献，请确认正文中包含“参考文献”章节。")
    return references, warnings


def format_document(text: str, style: str = "gb7714") -> dict:
    reference_heading = re.search(r"(?im)^\s*(参考文献|references|bibliography)\s*:?\s*$", text)
    body_text = text[: reference_heading.start()] if reference_heading else text
    paragraphs = split_paragraphs(body_text)
    references, warnings = format_references(text, style)
    formatted_text = "\n\n".join(paragraphs)
    if references:
        formatted_text += "\n\n参考文献\n\n" + "\n".join(reference.formatted for reference in references)
    return {
        "title": title_from_text(text),
        "style": STYLE_LABELS[style],
        "body_text": body_text,
        "formatted_text": formatted_text.strip(),
        "references": [asdict(reference) for reference in references],
        "warnings": warnings,
        "paragraph_count": len(paragraphs),
        "reference_count": len(references),
        "character_count": len(text),
    }
