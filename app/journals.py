from __future__ import annotations

from .storage import Store


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
    existing = store.list_journal_styles()
    if any(s["is_builtin"] for s in existing):
        return
    for journal in BUILTIN_JOURNALS:
        store.add_journal_style(
            name=journal["name"],
            publisher=journal["publisher"],
            rules=journal["rules"],
            is_builtin=True,
        )


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

    author_list = [a.strip() for a in authors.split(",") if a.strip()]
    max_et_al = rules.get("max_authors_et_al", 5)
    if len(author_list) > max_et_al:
        author_str = author_list[0] + " et al."
    else:
        author_str = rules.get("author_separator", ", ").join(author_list)

    year_fmt = rules.get("year_format", "no_parentheses")
    if year_fmt == "parentheses":
        year_str = f"({year})" if year and year != "n.d." else "(n.d.)"
    else:
        year_str = year if year else "n.d."

    parts = [author_str, year_str, title]
    if source:
        parts.append(source)
    if volume:
        vol_str = volume
        if issue:
            vol_str += f"({issue})"
        parts.append(vol_str)
    if pages:
        prefix = rules.get("pages_prefix", "")
        parts.append(f"{prefix}{pages}" if prefix else pages)
    if doi:
        prefix = rules.get("doi_prefix", "")
        parts.append(f"{prefix} {doi}" if prefix else doi)
    elif url:
        parts.append(url)

    return ". ".join(parts) + "."