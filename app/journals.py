from __future__ import annotations

import re

from .storage import Store


FULL_LAYOUT_RULES = {
    "page_size": "A4",
    "margin_top": "2.54",
    "margin_bottom": "2.54",
    "margin_left": "3.18",
    "margin_right": "3.18",
    "font_family": "SimSun",
    "font_size": "12pt",
    "line_spacing": "1.5",
    "first_line_indent": "2chars",
    "body_alignment": "both",
    "heading1_font": "SimHei",
    "heading2_font": "SimHei",
    "heading3_font": "SimHei",
    "ref_font": "SimSun",
    "page_header": "",
    "page_number_pos": "center",
    "figure_caption": "below",
    "citation_style": "superscript",
    "sort_order": "citation_order",
    "abstract_max_chars": 300,
}


def _merge_rules(ref_rules: dict) -> dict:
    rules = dict(FULL_LAYOUT_RULES)
    rules.update(ref_rules)
    return rules


BUILTIN_JOURNALS = [
    {
        "name": "Nature",
        "publisher": "Nature Publishing Group",
        "rules": {
            "author_format": "surname_initial",
            "author_separator": ", ",
            "max_authors_et_al": 5,
            "year_format": "no_parentheses",
            "title_case": "sentence",
            "journal_italic": True,
            "volume_bold": True,
            "pages_prefix": "pp.",
            "number_prefix": "",
            "doi_prefix": "doi:",
        },
    },
    {
        "name": "Science",
        "publisher": "AAAS",
        "rules": {
            "author_format": "surname_initial",
            "author_separator": ", ",
            "max_authors_et_al": 5,
            "year_format": "no_parentheses",
            "title_case": "sentence",
            "journal_italic": True,
            "volume_bold": False,
            "pages_prefix": "pp.",
            "number_prefix": "",
            "doi_prefix": "doi:",
        },
    },
    {
        "name": "IEEE Transactions",
        "publisher": "IEEE",
        "rules": {
            "author_format": "initial_surname",
            "author_separator": ", ",
            "max_authors_et_al": 6,
            "year_format": "no_parentheses",
            "title_case": "title",
            "journal_italic": True,
            "volume_bold": False,
            "pages_prefix": "pp.",
            "number_prefix": "noE",
            "doi_prefix": "doi:",
        },
    },
    {
        "name": "ACM",
        "publisher": "Association for Computing Machinery",
        "rules": {
            "author_format": "surname_initial",
            "author_separator": ", ",
            "max_authors_et_al": 3,
            "year_format": "parentheses",
            "title_case": "sentence",
            "journal_italic": False,
            "volume_bold": False,
            "pages_prefix": "pp.",
            "number_prefix": "no.",
            "doi_prefix": "doi:",
        },
    },
    {
        "name": "Elsevier (Numbered)",
        "publisher": "Elsevier",
        "rules": {
            "author_format": "surname_initial",
            "author_separator": ", ",
            "max_authors_et_al": 6,
            "year_format": "no_parentheses",
            "title_case": "sentence",
            "journal_italic": True,
            "volume_bold": True,
            "pages_prefix": "pp.",
            "number_prefix": "",
            "doi_prefix": "doi:",
        },
    },
    {
        "name": "Springer (Basic)",
        "publisher": "Springer",
        "rules": {
            "author_format": "surname_initial",
            "author_separator": ", ",
            "max_authors_et_al": 5,
            "year_format": "parentheses",
            "title_case": "sentence",
            "journal_italic": True,
            "volume_bold": False,
            "pages_prefix": "pp.",
            "number_prefix": "",
            "doi_prefix": "doi:",
        },
    },
    {
        "name": "MLA",
        "publisher": "Modern Language Association",
        "rules": {
            "author_format": "surname_firstname",
            "author_separator": ", ",
            "max_authors_et_al": 3,
            "year_format": "parentheses",
            "title_case": "title",
            "journal_italic": True,
            "volume_bold": False,
            "pages_prefix": "pp.",
            "number_prefix": "no.",
            "doi_prefix": "",
        },
    },
    {
        "name": "Chicago",
        "publisher": "University of Chicago Press",
        "rules": {
            "author_format": "surname_firstname",
            "author_separator": ", ",
            "max_authors_et_al": 10,
            "year_format": "parentheses",
            "title_case": "title",
            "journal_italic": True,
            "volume_bold": False,
            "pages_prefix": "pp.",
            "number_prefix": "no.",
            "doi_prefix": "doi:",
        },
    },
    {
        "name": "Vancouver",
        "publisher": "ICMJE",
        "rules": {
            "author_format": "surname_initial",
            "author_separator": ", ",
            "max_authors_et_al": 6,
            "year_format": "no_parentheses",
            "title_case": "sentence",
            "journal_italic": False,
            "volume_bold": False,
            "pages_prefix": "pp.",
            "number_prefix": "",
            "doi_prefix": "doi:",
        },
    },
    {
        "name": "Harvard",
        "publisher": "Harvard",
        "rules": {
            "author_format": "surname_initial",
            "author_separator": ", ",
            "max_authors_et_al": 3,
            "year_format": "parentheses",
            "title_case": "sentence",
            "journal_italic": True,
            "volume_bold": False,
            "pages_prefix": "pp.",
            "number_prefix": "",
            "doi_prefix": "doi:",
        },
    },
]


def init_builtin_styles(store: Store) -> None:
    existing = {s["name"]: s for s in store.list_journal_styles() if s["is_builtin"]}
    for journal in BUILTIN_JOURNALS:
        rules = _merge_rules(journal["rules"])
        current = existing.get(journal["name"])
        if current:
            if current["publisher"] != journal["publisher"] or current["rules"] != rules:
                store.update_journal_style(current["id"], rules, journal["publisher"])
        else:
            store.add_journal_style(name=journal["name"], publisher=journal["publisher"], rules=rules, is_builtin=True)


def list_styles(store: Store) -> list[dict]:
    return store.list_journal_styles()


def get_style(store: Store, style_id: int) -> dict | None:
    return store.get_journal_style(style_id)


def create_custom_style(store: Store, name: str, rules: dict, publisher: str = "", created_by: int | None = None) -> int:
    if not name:
        raise ValueError("格式名称不能为空。")
    return store.add_journal_style(name=name, rules=rules, publisher=publisher, is_builtin=False, created_by=created_by)


def delete_custom_style(store: Store, style_id: int) -> bool:
    return store.delete_journal_style(style_id)


def format_reference_by_rules(ref: dict, rules: dict, index: int) -> str:
    authors = ref.get("authors", "")
    year = ref.get("year", "").replace("n.d.", "n.d.")
    title = ref.get("title", "")
    source = ref.get("source", "")
    volume = ref.get("volume", "")
    issue = ref.get("issue", "")
    pages = ref.get("pages", "")
    doi = ref.get("doi", "")
    url = ref.get("url", "")

    author_list = ref.get("author_list") or [a.strip() for a in authors.split(",") if a.strip()]
    max_et_al = rules.get("max_authors_et_al", 5)
    if len(author_list) > max_et_al:
        author_list = author_list[:1]
        author_str = _format_author(author_list[0], rules.get("author_format", "surname_initial")) + " et al."
    else:
        author_str = rules.get("author_separator", ", ").join(
            _format_author(author, rules.get("author_format", "surname_initial")) for author in author_list
        )

    year_fmt = rules.get("year_format", "no_parentheses")
    if year_fmt == "parentheses":
        year_str = f"({year})" if year and year != "n.d." else "(n.d.)"
    else:
        year_str = year if year else "n.d."

    title = _format_title(title, rules.get("title_case", "sentence"))
    parts = [part for part in (author_str, year_str, title) if part]
    if source:
        parts.append(source)
    if volume:
        vol_str = volume
        if issue:
            vol_str += f"{rules.get('number_prefix', '')}{issue}" if rules.get("number_prefix") else f"({issue})"
        parts.append(vol_str)
    if pages:
        prefix = rules.get("pages_prefix", "")
        parts.append(f"{prefix}{pages}" if prefix else pages)
    if doi:
        prefix = rules.get("doi_prefix", "")
        parts.append(f"{prefix} {doi}" if prefix else doi)
    elif url:
        parts.append(url)

    citation_prefix = rules.get("citation_number_prefix", "")
    if not citation_prefix and rules.get("citation_style") == "bracket":
        citation_prefix = "brackets"
    if citation_prefix == "brackets":
        prefix = f"[{index}] "
    elif citation_prefix == "dot":
        prefix = f"{index}. "
    else:
        prefix = ""
    return prefix + ". ".join(parts) + "."


def _format_author(author: str, author_format: str) -> str:
    author = author.strip()
    if not author or any("\u4e00" <= char <= "\u9fff" for char in author):
        return author
    if "," in author:
        surname, given = [part.strip() for part in author.split(",", 1)]
    else:
        bits = author.split()
        surname, given = (bits[-1], " ".join(bits[:-1])) if len(bits) > 1 else (author, "")
    initials = "".join(part[0].upper() for part in re.split(r"[\s-]+", given) if part)
    if author_format == "initial_surname":
        return f"{initials} {surname}".strip()
    if author_format == "surname_firstname":
        return f"{surname}, {given}".strip(", ")
    return f"{surname} {initials}".strip()


def _format_title(title: str, title_case: str) -> str:
    if title_case == "title":
        return " ".join(word.capitalize() for word in title.split())
    if title_case == "sentence" and title:
        return title[:1].upper() + title[1:]
    return title


def sort_references(references: list[dict], sort_order: str) -> list[dict]:
    if sort_order in {"author", "alphabetical"}:
        return sorted(references, key=lambda ref: (ref.get("authors", "").lower(), ref.get("year", "")))
    if sort_order == "year":
        return sorted(references, key=lambda ref: (ref.get("year", ""), ref.get("authors", "").lower()))
    return list(references)
