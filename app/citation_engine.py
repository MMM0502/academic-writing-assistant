"""Citation rendering shared by the web preview and all exporters.

The parser produces structured reference dictionaries.  This module is the
single place where citation order, punctuation, numbering, and field labels
are rendered.  Journal templates are intentionally kept separate: they may
change Word typography without changing the citation grammar.
"""

from __future__ import annotations

import re


def _authors(ref: dict, style: str, rules: dict) -> str:
    authors = ref.get("author_list") or [a.strip() for a in ref.get("authors", "").split(",") if a.strip()]
    if not authors:
        return ""
    limit = int(rules.get("max_authors_et_al", 6) or 6)
    if len(authors) > limit:
        authors = authors[:1]
        suffix = " et al." if style != "gb7714" else " 等"
    else:
        suffix = ""
    # GB/APA/IEEE all conventionally use surname + initials for this input
    # shape ("Smith J"). Preserve Chinese names as supplied.
    rendered = []
    for author in authors:
        author = author.strip()
        if any("\u4e00" <= char <= "\u9fff" for char in author):
            rendered.append(author)
            continue
        bits = author.replace(",", " ").split()
        if len(bits) > 1:
            rendered.append(f"{bits[0]} {' '.join(bits[1:])}")
        else:
            rendered.append(author)
    separator = rules.get("author_separator", ", ")
    return separator.join(rendered) + suffix


def _title(value: str, rules: dict) -> str:
    mode = rules.get("title_case", "sentence")
    if mode == "title":
        return " ".join(word.capitalize() for word in value.split())
    if mode == "sentence" and value:
        return value[:1].upper() + value[1:]
    return value


def _number(index: int, style: str, rules: dict) -> str:
    if style == "ieee" or rules.get("citation_style") == "bracket":
        return f"[{index}] "
    if style == "gb7714":
        return f"[{index}] "
    return ""


def render_reference(ref: dict, index: int, style: str = "gb7714", rules: dict | None = None) -> str:
    rules = rules or {}
    author = _authors(ref, style, rules)
    year = ref.get("year") or "n.d."
    title = _title(ref.get("title", ""), rules)
    source = ref.get("source", "")
    volume = ref.get("volume", "")
    issue = ref.get("issue", "")
    pages = ref.get("pages", "")
    doi = ref.get("doi", "")
    url = ref.get("url", "")

    if style == "apa7":
        pieces = [author, f"({year})", f"{title}."]
        if source:
            journal = source
            if volume:
                journal += f", {volume}"
                if issue:
                    journal += f"({issue})"
            if pages:
                journal += f", {pages}"
            pieces.append(journal)
        text = " ".join(piece for piece in pieces if piece)
    elif style == "ieee":
        text = f'{author}, "{title},"' if author else f'"{title},"'
        if source:
            text += f" {source}"
        if volume:
            text += f", vol. {volume}"
        if issue:
            text += f", no. {issue}"
        if pages:
            text += f", pp. {pages}"
        text += f", {year}"
    else:
        text = ". ".join(piece for piece in (author, title) if piece)
        if source:
            text += f". {source}"
        if volume:
            text += f", {volume}"
        if issue:
            text += f"({issue})"
        if pages:
            text += f": {pages}"
        if year:
            text += f", {year}"

    if doi:
        text += f". DOI:{doi}"
    elif url:
        text += f". {url}"
    return _number(index, style, rules) + text.rstrip(".") + "."


def render_references(references: list[dict], style: str, rules: dict | None = None) -> list[dict]:
    rules = rules or {}
    order = rules.get("sort_order", "citation_order")
    refs = list(references)
    if order in {"alphabetical", "author"}:
        refs.sort(key=lambda item: (item.get("authors", "").lower(), item.get("year", "")))
    elif order == "year":
        refs.sort(key=lambda item: (item.get("year", ""), item.get("authors", "").lower()))
    for index, ref in enumerate(refs, start=1):
        ref["index"] = index
        ref["formatted"] = render_reference(ref, index, style, rules)
    return refs
