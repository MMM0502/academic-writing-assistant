from __future__ import annotations

from dataclasses import dataclass, asdict, field
import re
from typing import Iterable

from .parsers import iter_reference_lines, split_paragraphs, title_from_text


STYLE_LABELS = {
    "gb7714": "GB/T 7714-2015",
    "apa7": "APA 7",
    "ieee": "IEEE",
}

REFERENCE_TYPE_LABELS = {
    "journal": "期刊论文",
    "conference": "会议论文",
    "thesis": "学位论文",
    "book": "图书",
    "web": "网页",
    "patent": "专利",
    "report": "报告",
    "unknown": "未识别",
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
    volume: str = ""
    issue: str = ""
    pages: str = ""
    doi: str = ""
    url: str = ""
    reference_type: str = "journal"
    confidence: str = "medium"
    errors: list = field(default_factory=list)
    author_list: list = field(default_factory=list)


def _normalize_spaces(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("．", ".").strip(" \t.;；。"))


def _extract_doi(line: str) -> str:
    match = re.search(r"\b(10\.\d{4,9}/[^\s,;)\]]+)", line)
    if not match:
        return ""
    return match.group(1).rstrip(".,);]")


def _extract_url(line: str) -> str:
    match = re.search(r"https?://[^\s,;)\]]+", line)
    if not match:
        return ""
    return match.group(0).rstrip(".,);]")


def _extract_volume_issue_pages(line: str) -> tuple[str, str, str, str]:
    volume = issue = pages = ""
    remaining = line

    combined = re.search(
        r"\b(\d+)\s*[\(\[]\s*(\d+)\s*[\)\]]\s*[:：]?\s*(\d+\s*[-–—]\s*\d+|\d+)",
        remaining,
    )
    if combined:
        volume = combined.group(1)
        issue = combined.group(2)
        pages = combined.group(3).replace("–", "-").replace("—", "-").strip()
        remaining = remaining[: combined.start()] + remaining[combined.end():]
        return volume, issue, pages, _normalize_spaces(remaining)

    vol_match = re.search(r"\bvol\.?\s*(\d+)", remaining, re.I)
    if vol_match:
        volume = vol_match.group(1)
        remaining = remaining[: vol_match.start()] + remaining[vol_match.end():]

    issue_match = re.search(r"\b(?:no|num)\.?\s*(\d+)", remaining, re.I)
    if issue_match:
        issue = issue_match.group(1)
        remaining = remaining[: issue_match.start()] + remaining[issue_match.end():]

    pages_match = re.search(r"\bpp\.?\s*(\d+\s*[-–—]\s*\d+|\d+)", remaining, re.I)
    if pages_match:
        pages = pages_match.group(1).replace("–", "-").replace("—", "-").strip()
        remaining = remaining[: pages_match.start()] + remaining[pages_match.end():]

    return volume, issue, pages, _normalize_spaces(remaining)


def _detect_reference_type(line: str, has_url: bool) -> str:
    lower = line.lower()
    if re.search(r"(博士论文|硕士论文|学位论文|dissertation|thesis)", lower):
        return "thesis"
    if re.search(r"(会议|conference|proceedings|proc\.|symposium|workshop)", lower):
        return "conference"
    if re.search(r"(专利|patent)", lower):
        return "patent"
    if re.search(r"(报告|technical report|tech\. rep)", lower):
        return "report"
    if has_url and not re.search(r"(期刊|journal|trans\.|ieee|acta)", lower):
        return "web"
    if re.search(r"(出版社|press|publishing|publisher)", lower):
        return "book"
    return "journal"


def _confidence_level(authors: str, year: str, title: str, source: str, extra: int) -> str:
    score = sum(1 for value in (authors, year, title, source) if value and value != "未知作者" and value != "n.d.")
    score += 1 if extra > 0 else 0
    if score >= 4:
        return "high"
    if score >= 2:
        return "medium"
    return "low"


def _is_chinese_text(text: str) -> bool:
    chinese_chars = len(re.findall(r"[\u4e00-\u9fff]", text))
    return chinese_chars > len(text) * 0.3 if text else False


def split_authors(authors_str: str) -> list[str]:
    if not authors_str or authors_str == "未知作者":
        return []
    s = authors_str.strip()
    s = re.sub(r"\s*[，,]?\s*(等|et\s+al\.?)\s*\.?$", "", s, flags=re.I).strip()
    if not s:
        return []

    if ";" in s:
        return [a.strip() for a in s.split(";") if a.strip()]

    if _is_chinese_text(s):
        if "，" in s or "," in s:
            parts = [a.strip() for a in re.split(r"[，,]", s) if a.strip()]
        else:
            parts = s.split()
        return parts if parts else [s]

    if re.match(r"^[A-Z][a-z]+,\s+[A-Z]", s):
        chunks = re.split(r",\s+(?=[A-Z][a-z]+,\s+[A-Z]\.)", s)
        if len(chunks) > 1:
            return [c.strip().rstrip(",") for c in chunks if c.strip()]

    parts = [a.strip() for a in re.split(r",\s*(?=[A-Z])", s) if a.strip()]
    return parts if parts else [s]


def _split_authors_title_source(line: str) -> tuple[str, str, str]:
    if not line:
        return "未知作者", "", ""

    is_chinese = _is_chinese_text(line)
    delimiter = r"[。.!?]\s+" if not is_chinese else r"[。.!?]\s+"
    parts = [p.strip() for p in re.split(delimiter, line, maxsplit=2) if p.strip()]

    if len(parts) >= 3:
        authors = parts[0]
        title = parts[1]
        source = parts[2]
    elif len(parts) == 2:
        authors = parts[0]
        title = parts[1]
        source = ""
    elif len(parts) == 1:
        if is_chinese:
            comma_parts = [p.strip() for p in re.split(r"[，,]", line) if p.strip()]
            if len(comma_parts) >= 2:
                authors = comma_parts[0]
                title = comma_parts[1]
                source = "，".join(comma_parts[2:]) if len(comma_parts) > 2 else ""
            else:
                authors = "未知作者"
                title = line
                source = ""
        else:
            authors = "未知作者"
            title = line
            source = ""
    else:
        authors = "未知作者"
        title = ""
        source = ""

    source = source.strip(" ,，；;.")
    return authors, title, source


def _validate_reference(authors: str, year: str, title: str, source: str, style: str) -> list[dict]:
    errors: list[dict] = []
    if not authors or authors == "未知作者":
        errors.append({"field": "authors", "message": "未识别出作者", "severity": "warning"})
    if not title:
        errors.append({"field": "title", "message": "未识别出题名", "severity": "warning"})
    if style == "apa7":
        if not year or year == "n.d.":
            errors.append({"field": "year", "message": "APA 7 要求标注年份，缺失时应用 (n.d.)", "severity": "info"})
    elif style == "ieee":
        if not source:
            errors.append({"field": "source", "message": "IEEE 要求标注来源（期刊/会议）", "severity": "info"})
    elif style == "gb7714":
        if not source:
            errors.append({"field": "source", "message": "GB/T 7714 建议标注来源", "severity": "info"})
    return errors


def _format_reference(
    index: int, authors: str, year: str, title: str, source: str,
    volume: str, issue: str, pages: str, doi: str, url: str, style: str,
) -> str:
    if style == "apa7":
        formatted = f"{authors} ({year}). {title}."
        if source:
            formatted += f" {source}"
            if volume:
                formatted += f", {volume}"
                if issue:
                    formatted += f"({issue})"
            if pages:
                formatted += f", {pages}"
        formatted += "."
    elif style == "ieee":
        formatted = f'[{index}] {authors}, "{title},"'
        if source:
            formatted += f" {source}"
            if volume:
                formatted += f", vol. {volume}"
            if issue:
                formatted += f", no. {issue}"
            if pages:
                formatted += f", pp. {pages}"
        formatted += f", {year}."
    else:
        formatted = f"{index}. {authors}. {title}"
        if source:
            formatted += f". {source}"
            if volume:
                formatted += f", {volume}"
                if issue:
                    formatted += f"({issue})"
            if pages:
                formatted += f": {pages}"
        formatted += f", {year}."
    if doi:
        formatted += f" DOI: {doi}."
    elif url:
        formatted += f" URL: {url}."
    return formatted


def parse_reference(raw: str, index: int, style: str) -> Reference:
    original = raw
    line = re.sub(r"^\s*(?:\[\d+\]|\d+[.)、])\s*", "", raw)
    line = _normalize_spaces(line)
    errors: list[dict] = []

    doi = _extract_doi(line)
    if doi:
        line = re.sub(re.escape(doi), "", line).strip(" ,.;；")

    url = _extract_url(line)
    if url:
        line = re.sub(re.escape(url), "", line).strip(" ,.;；")

    volume, issue, pages, line = _extract_volume_issue_pages(line)

    year_match = re.search(r"\b(19|20)\d{2}[a-z]?\b", line)
    year = year_match.group(0) if year_match else ""
    if year:
        line = re.sub(rf"\b{re.escape(year)}\b", "", line).strip(" ,.;；，")
    if not year:
        year = "n.d."
        errors.append({"field": "year", "message": "未识别出出版年份", "severity": "warning"})

    authors, title, source = _split_authors_title_source(line)
    author_list = split_authors(authors)

    reference_type = _detect_reference_type(original, bool(url))
    extra_fields = sum(1 for value in (volume, issue, pages, doi, url) if value)
    confidence = _confidence_level(authors, year, title, source, extra_fields)
    if confidence == "low":
        errors.append({"field": "overall", "message": "解析置信度较低，请人工核对", "severity": "warning"})

    formatted = _format_reference(index, authors, year, title, source, volume, issue, pages, doi, url, style)
    errors.extend(_validate_reference(authors, year, title, source, style))

    return Reference(
        index, raw, authors, year, title, source, formatted,
        reference_type=reference_type, volume=volume, issue=issue,
        pages=pages, doi=doi, url=url, confidence=confidence,
        errors=errors, author_list=author_list,
    )


def format_references(text: str, style: str = "gb7714") -> tuple[list[Reference], list[str]]:
    if style not in STYLE_LABELS:
        raise ValueError("不支持的参考文献格式。")
    lines = list(iter_reference_lines(text))
    if not lines:
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
        if reference.confidence == "low":
            warnings.append(f"第 {reference.index} 条解析置信度较低，请人工核对。")
        for err in reference.errors:
            if err["severity"] == "warning" and err["field"] != "year" and err["field"] != "overall":
                warnings.append(f"第 {reference.index} 条{err['message']}。")
    if not references:
        warnings.append("未识别到参考文献，请确认正文中包含\u201c参考文献\u201d章节。")
    return references, warnings


def extract_inline_citations(body_text: str) -> list[dict]:
    citations: list[dict] = []

    for match in re.finditer(r"\[(\d+(?:\s*[-–—]\s*\d+)?(?:\s*,\s*\d+(?:\s*[-–—]\s*\d+)?)*)\]", body_text):
        for number in _expand_citation_token(match.group(1)):
            citations.append({"type": "numeric", "value": number, "span": match.span()})

    for match in re.finditer(r"[\(\[]\s*([^()\[\]]+?,\s*(?:19|20)\d{2}[a-z]?)\s*[\)\]]", body_text):
        label = match.group(1).strip()
        citations.append({"type": "author-year", "value": label, "span": match.span()})

    return citations


def _expand_citation_token(token: str) -> list[int]:
    numbers: list[int] = []
    for part in re.split(r"\s*,\s*", token):
        part = part.strip()
        range_match = re.match(r"^(\d+)\s*[-–—]\s*(\d+)$", part)
        if range_match:
            start, end = int(range_match.group(1)), int(range_match.group(2))
            numbers.extend(range(start, end + 1))
        elif part.isdigit():
            numbers.append(int(part))
    return numbers


def check_citations(body_text: str, references: list[Reference]) -> dict:
    citations = extract_inline_citations(body_text)
    numeric_citations = [c["value"] for c in citations if c["type"] == "numeric"]
    author_year_citations = [c["value"] for c in citations if c["type"] == "author-year"]

    reference_numbers = {ref.index for ref in references}
    cited_numbers = set(numeric_citations)

    orphan_citations = sorted(cited_numbers - reference_numbers)
    unused_references = sorted(reference_numbers - cited_numbers)

    counts = {}
    for number in numeric_citations:
        counts[number] = counts.get(number, 0) + 1
    duplicate_numbers = sorted(number for number, count in counts.items() if count > 1)

    discontinuous_numbers = []
    if numeric_citations and reference_numbers:
        max_ref = max(reference_numbers)
        expected = set(range(1, max_ref + 1))
        missing = sorted(expected - reference_numbers)
        if missing:
            discontinuous_numbers = missing

    warnings: list[str] = []
    if orphan_citations:
        warnings.append(f"正文引用了参考文献列表中不存在的编号：{', '.join(map(str, orphan_citations))}。")
    if unused_references and numeric_citations:
        warnings.append(f"参考文献列表中以下编号在正文未出现引用：{', '.join(map(str, unused_references))}。")
    if duplicate_numbers:
        warnings.append(f"正文引用编号重复：{', '.join(map(str, duplicate_numbers))}。")
    if discontinuous_numbers:
        warnings.append(f"参考文献编号不连续，缺失：{', '.join(map(str, discontinuous_numbers))}。")

    return {
        "inline_citations": citations,
        "orphan_citations": orphan_citations,
        "unused_references": unused_references,
        "duplicate_numbers": duplicate_numbers,
        "discontinuous_numbers": discontinuous_numbers,
        "warnings": warnings,
        "has_issue": bool(warnings),
    }


def _split_body_and_references(text: str) -> tuple[str, str]:
    reference_heading = re.search(r"(?im)^\s*(参考文献|references|bibliography)\s*:?\s*$", text)
    if reference_heading:
        return text[: reference_heading.start()].strip(), text[reference_heading.start():].strip()
    return text.strip(), ""


def format_document(text: str, style: str = "gb7714") -> dict:
    body_text, _ = _split_body_and_references(text)
    paragraphs = split_paragraphs(body_text)
    references, warnings = format_references(text, style)
    formatted_text = "\n\n".join(paragraphs)
    if references:
        formatted_text += "\n\n参考文献\n\n" + "\n".join(reference.formatted for reference in references)
    citation_check = check_citations(body_text, references)
    return {
        "title": title_from_text(text),
        "style": STYLE_LABELS[style],
        "body_text": body_text,
        "formatted_text": formatted_text.strip(),
        "references": [asdict(reference) for reference in references],
        "warnings": warnings,
        "citation_check": citation_check,
        "paragraph_count": len(paragraphs),
        "reference_count": len(references),
        "character_count": len(text),
    }
