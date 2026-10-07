from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
import json
import re

from .llm import generate_review as generate_llm_review, status as llm_status
from .parsers import title_from_text


MISSING = "\u672a\u8bc6\u522b"
UNIDENTIFIED_AUTHOR = "\u4f5c\u8005\u672a\u8bc6\u522b"
UNIDENTIFIED_YEAR = "\u5e74\u4efd\u672a\u8bc6\u522b"

STOPWORDS = {
    "the", "and", "of", "with", "from", "study", "using", "paper", "research",
    "based", "method", "analysis", "introduction", "abstract", "result", "results",
    "journal", "volume", "issue", "vol", "no", "issn", "doi", "university", "college",
    "public", "relations", "forum",
    "pworld", "prworld",
    "\u7814\u7a76", "\u65b9\u6cd5", "\u8fdb\u884c", "\u901a\u8fc7", "\u5206\u6790", "\u672c\u6587",
    "\u7ed3\u679c", "\u57fa\u4e8e", "\u7cfb\u7edf", "\u6570\u636e", "\u8868\u660e", "\u7814\u7a76\u8868\u660e",
    "\u7684", "\u95ee\u9898", "\u4e00\u65b9\u9762", "\u53e6\u4e00\u65b9\u9762", "\u5176\u4e2d", "\u6458\u8981",
    "\u516c\u5173\u4e16\u754c",
}

COMMON_PHRASES = {
    "higher education", "environmental science", "data science", "big data",
    "artificial intelligence", "digital education", "vocational education",
    "machine learning", "deep learning", "accounting major", "economic development",
}


@dataclass
class LiteratureItem:
    title: str
    year: str
    text: str
    keywords: list[str]
    authors: str = ""
    source: str = ""
    doi: str = ""
    filename: str = ""
    abstract: str = ""
    methods: str = ""
    findings: str = ""
    limitations: str = ""
    evidence_engine: str = "local-rule-engine"


def _clean(value: str, limit: int = 360) -> str:
    value = re.sub(r"\s+", " ", value or "").strip(" \t\r\n")
    return value if len(value) <= limit else value[:limit].rstrip() + "..."


def _keywords(text: str, limit: int = 8) -> list[str]:
    text = _remove_layout_noise(_before_references(text))
    explicit = _explicit_keywords(text)
    if explicit:
        return explicit[:limit]
    tokens = [token.lower() for token in re.findall(r"[A-Za-z][A-Za-z-]{2,}|[\u4e00-\u9fff]{2,8}", text)]
    counts = Counter(token for token in tokens if _keyword_token_ok(token, counts=None))
    phrases = Counter(
        f"{left} {right}"
        for left, right in zip(tokens, tokens[1:])
        if _keyword_token_ok(left, counts=None)
        and _keyword_token_ok(right, counts=None)
        and re.fullmatch(r"[a-z][a-z-]*", left)
        and re.fullmatch(r"[a-z][a-z-]*", right)
    )
    selected: list[str] = []
    used_words: set[str] = set()
    for phrase, frequency in phrases.most_common():
        if frequency < 2 and phrase not in COMMON_PHRASES:
            continue
        left, right = phrase.split(" ", 1)
        if left in used_words or right in used_words:
            continue
        selected.append(phrase)
        used_words.update((left, right))
        if len(selected) >= limit:
            return selected
    for token, _ in counts.most_common():
        if token in used_words:
            continue
        selected.append(token)
        if len(selected) >= limit:
            break
    return selected


def _explicit_keywords(text: str) -> list[str]:
    for line in (text or "").splitlines():
        match = re.search(r"(?:关\s*键\s*词|keywords?)\s*[:：]?\s*(.+)$", line, re.I)
        if not match:
            continue
        values = re.split(r"[；;、,，|]+", match.group(1))
        cleaned = []
        for value in values:
            value = re.sub(r"\s+", " ", value).strip(" .:：;；,，")
            if value and len(value) >= 2 and value.lower() not in STOPWORDS:
                cleaned.append(value.lower() if re.fullmatch(r"[A-Za-z][A-Za-z -]*", value) else value)
        if cleaned:
            return list(dict.fromkeys(cleaned))
    return []


def _keyword_token_ok(token: str, counts: Counter | None = None) -> bool:
    if token in STOPWORDS or len(token) < 3:
        return False
    if re.fullmatch(r"[a-z][a-z-]*", token) and len(token) == 3:
        # Short lowercase OCR fragments such as "ono" are not useful clues.
        if counts is None or counts.get(token, 0) < 2:
            return token in {"esg"}
    return True


def _lines(text: str) -> list[str]:
    result = []
    for raw in text.splitlines():
        line = re.sub(r"^\s*[#>*-]+\s*", "", raw).strip()
        if line:
            result.append(line)
    return result


def _sentences(text: str) -> list[str]:
    # Do not treat line wrapping or semicolons as sentence boundaries. In
    # particular, PDF extraction often removes line breaks and punctuation;
    # any unfinished tail must stay unquoted rather than become fake evidence.
    normalized = re.sub(r"\s+", " ", text or "").strip()
    parts = re.split(r"(?<=[。！？!?])\s*", normalized)
    return [
        part.strip()
        for part in parts
        if part.strip()
        and re.search(r"[。！？!?]$", part.strip())
        and not re.match(r"^[\u4e00-\u9fff]{1,2}[，,]", part.strip())
        and not re.match(r"^其中[，,]", part.strip())
    ]


def _labeled_value(lines: list[str], labels: tuple[str, ...]) -> str:
    label_pattern = "|".join(labels)
    inline = re.compile(rf"^(?:{label_pattern})\s*[:：]\s*(.+)$", re.I)
    heading = re.compile(rf"^(?:{label_pattern})\s*$", re.I)
    for index, line in enumerate(lines):
        match = inline.match(line)
        if match:
            return _clean(match.group(1))
        if heading.match(line):
            following = []
            for candidate in lines[index + 1 : index + 4]:
                if re.match(r"^(?:摘要|方法|研究方法|结果|结论|局限|不足|abstract|method|results?|conclusion)", candidate, re.I):
                    break
                following.append(candidate)
            if following:
                return _clean(" ".join(following))
    return ""


def _section_value(lines: list[str], labels: tuple[str, ...], stop_labels: tuple[str, ...]) -> str:
    """Collect a labeled section across PDF line wraps until the next section."""
    label_pattern = "|".join(labels)
    stop_pattern = "|".join(stop_labels)
    inline = re.compile(rf"^(?:{label_pattern})\s*[:：]?\s*(.*)$", re.I)
    for index, line in enumerate(lines):
        match = inline.match(line)
        if not match:
            continue
        values = [match.group(1).strip()] if match.group(1).strip() else []
        for candidate in lines[index + 1 : index + 32]:
            if re.match(rf"^(?:{stop_pattern})\s*[:：]?(?:\s|$)", candidate, re.I):
                break
            if re.match(r"^(?:摘要|关键词|关键字|abstract|keywords?|作者简介|通讯作者|参考文献|引言|结语|结论|结果|研究结果|研究方法|方法|局限|不足|展望|一、|二、|三、|\(?\d+[.、)]?)\s*", candidate, re.I):
                break
            values.append(candidate)
        return _clean(" ".join(values), limit=2400)
    return ""


def _extract_evidence(text: str, kind: str) -> str:
    sentences = _sentences(text)
    if kind == "method":
        patterns = r"(?:采用|运用|使用|通过).{0,24}(?:问卷|访谈|实验|回归|实证|案例|文本分析|计量|模型)|(?:methodology|methods?|survey|experiment|regression|case study)"
    elif kind == "finding":
        patterns = r"(?:研究结果|结果表明|研究发现|发现|结论是|结果显示|显著|findings?|conclusion|significant|suggests?)"
    else:
        patterns = r"局限|不足|展望|未来|limitations?|future work"
    matches = [sentence for sentence in sentences if re.search(patterns, sentence, re.I)]
    return _clean(" ".join(matches[:3]))


def _method_label(methods: str) -> str:
    labels = [
        (r"问卷|survey", "问卷调查"),
        (r"访谈|质性|qualitative", "质性访谈"),
        (r"实验|experiment", "实验研究"),
        (r"回归|计量|实证|regression|empirical", "实证/计量"),
        (r"案例|case study", "案例研究"),
        (r"文本分析|内容分析|text analysis|content analysis", "文本/内容分析"),
        (r"模型|算法|machine learning|deep learning", "模型/算法"),
        (r"理论|概念|theoretical", "理论分析"),
    ]
    for pattern, label in labels:
        if re.search(pattern, methods, re.I):
            return label
    return MISSING


def _metadata(text: str, filename: str) -> tuple[str, str, str, str, str]:
    source_text = _before_references(text)
    lines = _lines(source_text)
    fallback = re.sub(r"\.[^.]+$", "", filename).strip() or "\u672a\u547d\u540d\u6587\u732e"
    filename_title = _filename_title(filename)
    title = filename_title or re.sub(r"^\s*#+\s*", "", title_from_text(source_text, fallback)).strip()
    title = re.sub(r"^(?:\u6807\u9898|title)\s*[:：]\s*", "", title, flags=re.I)
    # Bibliography entries later in the PDF belong to cited works, not
    # necessarily to the uploaded paper. Only inspect the front matter.
    front_matter = "\n".join(lines[:16])
    years = re.findall(r"\b(?:19|20)\d{2}\b", front_matter)
    year = years[0] if years else ""
    authors = _labeled_value(lines[:12], ("作者", "authors?", "author"))
    source = _labeled_value(lines[:12], ("期刊", "会议", "出版社", "journal", "conference", "publisher", "source"))
    doi_match = re.search(r"\b10\.\d{4,9}/[-._;()/:A-Z0-9]+\b", front_matter, re.I)
    doi = doi_match.group(0).rstrip(".,;)") if doi_match else ""
    # Do not guess an author from arbitrary title-page/body lines. False
    # authors are worse than an omitted reference.
    return title or fallback, year, authors, source, doi


def _filename_title(filename: str) -> str:
    """Prefer a descriptive upload filename over damaged PDF front matter."""
    stem = re.sub(r"\.[^.]+$", "", filename or "").strip()
    stem = re.sub(r"^[\s_\-]+|[\s_\-]+$", "", stem)
    stem = re.sub(r"[_]+", " ", stem)
    stem = re.sub(r"\s+", " ", stem).strip()
    if not stem or stem.lower() in {
        "paper", "document", "article", "manuscript", "upload", "uploaded-paper",
        "new document", "\u672a\u547d\u540d", "\u672a\u547d\u540d\u6587\u732e",
    }:
        return ""
    if re.fullmatch(r"(?:paper|document|article)[-_ ]?\d*", stem, re.I):
        return ""
    return stem if len(stem) >= 4 else ""


def _before_references(text: str) -> str:
    match = re.search(r"(?im)^\s*(?:参考文献|引用文献|bibliography|references)\s*[:：]?\s*$", text or "")
    return text[:match.start()] if match else (text or "")


def _remove_layout_noise(text: str) -> str:
    text = re.sub(r"(?im)=+\s*第\s*\d+\s*页(?:（?OCR）?)?\s*=+", " ", text or "")
    text = re.sub(r"(?im)=+\s*page\s*\d+.*?=+", " ", text)
    text = re.sub(r"(?i)P\s*UBLIC\s+RELATIONS\s+FORUM", "", text or "")
    text = re.sub(r"(?i)\bp(?:r)?world\b|\bpublic\s*world\b", "", text)
    text = re.sub(r"(?im)^\s*(?:19|20)\d{2}\s*年?\s*\d{1,2}\s*月?.{0,24}\b(?:journal|jou)\b.*$", "", text)
    text = re.sub(r"(?im)^\s*10\.\d{4,9}/\S+\s*$", "", text)
    text = re.sub(r"(?im)^\s*[A-Za-z]?\s*[.·-]?\s*\d{1,3}\s*$", "", text)
    return text


def _evidence_excerpt(value: str, limit: int = 2) -> str:
    sentences = _sentences(value)
    # Keep whole source sentences only. An overlong/OCR-damaged sentence is
    # omitted instead of being cut mid-sentence and presented as a quote.
    complete = [sentence for sentence in sentences if len(sentence) <= 500]
    return " ".join(complete[:limit])


def _clean_evidence(value: str, title: str) -> str:
    value = _remove_layout_noise(value)
    value = re.sub(r"(?i)\b(?:摘要|abstract)\s*[:：]?", "", value)
    if title:
        value = value.replace(title, "")
    return _evidence_excerpt(value).strip(" ，,：:;")


def _clean_section(value: str, title: str) -> str:
    value = _remove_layout_noise(value)
    value = re.sub(r"(?i)\b(?:摘要|abstract)\s*[:：]?", "", value)
    # PDF/OCR and model output may include the section heading itself.
    value = re.sub(
        r"(?im)^\s*(?:\d+(?:\.\d+)*\s*)?(?:研究)?(?:局限(?:性)?(?:及展望)?|不足(?:及展望)?|及展望|展望|研究方法|方法|研究结果|结果|结论|摘要|abstract)\s*[:：]?\s*",
        "",
        value,
    )
    value = re.sub(r"(?im)^\s*\d+(?:\.\d+)*\s+研究局限及展望\s*", "", value)
    # OCR/LLM may leave the tail of the heading after its number was removed.
    value = re.sub(r"^\s*(?:及展望|局限及展望|研究局限及展望)\s*[:：]?\s*", "", value)
    if title:
        value = value.replace(title, "")
    return _clean(value, limit=2400).strip(" ，,：:;")


def _looks_like_reference(value: str) -> bool:
    """Reject bibliography/layout text that an LLM may have attached to a field."""
    return bool(re.search(
        r"(?i)(?:\[\s*[A-Z]?\s*\d+\s*\]|\[J\]|\bdoi\s*[:：]?\s*10\.|"
        r"international journal|journal of|\bvol\.?\s*\d|\bno\.?\s*\d|研究局限及展望|参考文献|references?)",
        value or "",
    ))


def _validated_ai_value(value: str, title: str, field: str) -> str:
    value = _clean_section(value, title)
    if not value or _looks_like_reference(value):
        return ""
    # A limitations field must describe a limitation or future direction. A
    # bibliography-like paragraph without such a signal is not evidence.
    if field == "limitations" and not re.search(
        r"局限|不足|限制|展望|未来|样本|数据|研究范围|可推广|边界|缺乏|有待|进一步|future|limitation",
        value,
        re.I,
    ):
        return ""
    if field == "limitations" and re.search(
        r"(?i)OCR|RUE|Brey|BESET|\bBSE\b|第\s*\d+\s*页|页眉|乱码",
        value,
    ):
        return ""
    return value[:2400]


def _document_evidence(text: str) -> tuple[str, str, str, str]:
    text = _remove_layout_noise(_before_references(text))
    lines = _lines(text)
    abstract = _section_value(
        lines,
        ("摘要", r"摘\s*要", "abstract"),
        ("关键词", "关键字", "keywords?", "作者简介", "通讯作者", "引言", "introduction", "abstract"),
    ) or _labeled_value(lines, ("摘要", "abstract"))
    methods = _section_value(
        lines,
        ("研究方法", "方法", "methodology", "methods?"),
        ("结果", "研究结果", "结论", "results?", "conclusion", "局限", "不足", "展望", "limitations?", "future work"),
    ) or _labeled_value(lines, ("研究方法", "方法", "methodology", "methods", "method"))
    findings = _section_value(
        lines,
        ("研究结果", "结果", "结论", "results?", "conclusion"),
        ("局限", "不足", "展望", "limitations?", "future work", "参考文献", "references?"),
    ) or _labeled_value(lines, ("研究结果", "结果", "结论", "results?", "conclusion"))
    limitations = _section_value(
        lines,
        ("研究不足", "局限", "不足", "展望", "limitations?", "future work"),
        ("参考文献", "references?", "bibliography"),
    ) or _labeled_value(lines, ("研究不足", "局限", "不足", "limitations?", "future work"))
    # The title is known at the caller level only; remove repeated running
    # heads and labels here, while keeping complete source sentences.
    abstract = _evidence_excerpt(abstract)
    methods = _evidence_excerpt(methods or _extract_evidence(text, "method"))
    findings = _evidence_excerpt(findings or _extract_evidence(text, "finding"))
    limitations = _evidence_excerpt(limitations or _extract_evidence(text, "limitation"))
    return abstract, methods, findings, limitations


def build_item(text: str, filename: str) -> LiteratureItem:
    title, year, authors, source, doi = _metadata(text, filename)
    abstract, methods, findings, limitations = _document_evidence(text)
    abstract = _clean_section(abstract, title)
    methods = _clean_section(methods, title)
    findings = _clean_section(findings, title)
    limitations = _clean_section(limitations, title)
    if _looks_like_reference(limitations):
        limitations = ""
    return LiteratureItem(
        title=title,
        year=year,
        text=text,
        keywords=_keywords(text),
        authors=authors,
        source=source,
        doi=doi,
        filename=filename,
        abstract=abstract,
        methods=methods,
        findings=findings,
        limitations=limitations,
    )


def _parse_json_object(value: str) -> dict | None:
    value = (value or "").strip()
    value = re.sub(r"^```(?:json)?\s*|\s*```$", "", value, flags=re.I | re.S).strip()
    start, end = value.find("{"), value.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        parsed = json.loads(value[start : end + 1])
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _ai_document_evidence(item: LiteratureItem) -> bool:
    """Use the model to locate labeled evidence, without changing the title."""
    prompt = (
        "请从下面上传论文的原文中提取四个字段，并只返回 JSON，不要 Markdown。"
        "字段为 abstract、methods、findings、limitations。JSON 的值只能是原文连续、完整的句子，"
        "不要在值里重复字段名、章节标题、编号或‘研究局限及展望’；如果无法确认完整句，返回空字符串。"
        "不要改写、不要补充常识、不要使用参考文献中的内容；原文没有明确证据时返回空字符串。"
        "特别是 limitations 只能从原文明确标注‘局限/研究不足/展望/未来研究’的段落提取，"
        "不能根据摘要、研究方法或结果自行推测局限；没有这类明确段落就返回空字符串。"
        "摘要可以跨 PDF 换行拼接，但不得把正文或参考文献当摘要。\n\n"
        f"文件名：{item.filename}\n论文标题（仅供定位）：{item.title}\n\n原文：\n{item.text[:16000]}"
    )
    response = generate_review_with_llm(prompt)
    parsed = _parse_json_object(response or "")
    if not parsed:
        return False
    changed = False
    for field in ("abstract", "methods", "findings", "limitations"):
        value = parsed.get(field)
        if isinstance(value, str):
            value = _validated_ai_value(value, item.title, field)
            if value:
                setattr(item, field, value[:2400])
                changed = True
    if changed:
        item.evidence_engine = "ai-assisted"
    return changed


def _enhance_document_evidence(items: list[LiteratureItem]) -> None:
    if not llm_status().get("configured"):
        return
    for item in items:
        _ai_document_evidence(item)


def _citation(item: LiteratureItem, index: int) -> str | None:
    if not item.authors or not item.year or not item.title or not (item.source or item.doi):
        return None
    citation = f"{index}. {item.authors}. {item.title}. {item.year}."
    if item.source:
        citation += f" {item.source}."
    if item.doi:
        citation += f" DOI: {item.doi}."
    return citation


def _summary_block(item: LiteratureItem, index: int) -> str:
    method = item.methods or MISSING
    finding = item.findings or MISSING
    abstract = item.abstract or MISSING
    limitation = item.limitations or MISSING
    year = item.year or UNIDENTIFIED_YEAR
    return (
        f"### {index}. {item.title}（{year}）\n"
        f"- 研究问题/摘要：{abstract}\n"
        f"- 研究方法：{method}\n"
        f"- 核心发现：{finding}\n"
        f"- 局限或展望：{limitation}"
    )


def generate_local_review(items: list[LiteratureItem], topic: str = "") -> dict:
    if not items:
        raise ValueError("\u81f3\u5c11\u4e0a\u4f20\u4e00\u7bc7\u53ef\u8bfb\u53d6\u7684\u6587\u732e")
    topic = topic.strip() or "\u6587\u732e\u7814\u7a76\u4e3b\u9898"
    years = sorted({item.year for item in items if item.year})
    method_counts = Counter(_method_label(item.methods) for item in items)
    method_counts.pop(MISSING, None)
    summaries = [_summary_block(item, index) for index, item in enumerate(items, start=1)]
    evidence = [item for item in items if item.findings]
    methods = [item for item in items if item.methods]
    limitations = [item for item in items if item.limitations]
    references = []
    for index, item in enumerate(items, start=1):
        citation = _citation(item, index)
        if citation:
            references.append({
                "index": index,
                "citation": citation,
                "title": item.title,
                "authors": item.authors,
                "year": item.year,
                "source": item.source,
                "doi": item.doi,
                "filename": item.filename,
            })
    year_range = f"{years[0]}\u2014{years[-1]}" if years else UNIDENTIFIED_YEAR
    method_overview = "、".join(f"{name}（{count}篇）" for name, count in method_counts.items()) or MISSING
    problem_lines = "\n".join(f"- {index}. {item.title}：{item.abstract or MISSING}" for index, item in enumerate(items, start=1))
    finding_lines = "\n".join(f"- {index}. {item.title}：{item.findings or MISSING}" for index, item in enumerate(items, start=1))
    method_lines = "\n".join(f"- {index}. {item.title}：{item.methods or MISSING}" for index, item in enumerate(items, start=1))
    viewpoint_intro = (
        f"当前已从 {len(evidence)}/{len(items)} 篇文献中提取到带有结果、发现或结论标记的内容。"
        "下面保留各文献中的证据句，不把关键词频次当作作者观点；不同文献之间是否形成一致结论，需要结合研究对象和方法进一步核对。"
    )
    method_intro = (
        f"当前已从 {len(methods)}/{len(items)} 篇文献中提取到方法线索。"
        "方法类型只在原文出现明确线索时归类，未识别的文献不会被强行归入某种方法。"
    )
    gap_lines = "\n".join(
        [
            f"- 已识别研究方法的文献：{len(methods)}/{len(items)} 篇。",
            f"- 已识别核心发现的文献：{len(evidence)}/{len(items)} 篇。",
            f"- 明确写出局限或展望的文献：{len(limitations)}/{len(items)} 篇。",
            "- 对于标记为“未识别”的项目，需要回到原文核对，系统不会用关键词补写结论。",
        ]
    )
    markdown = (
        f"# {topic}\u6587\u732e\u7efc\u8ff0\n\n"
        f"## \u4e00\u3001\u6587\u732e\u8303\u56f4\u4e0e\u7814\u7a76\u95ee\u9898\n"
        f"本综述汇总 {len(items)} 篇文献，时间范围为 {year_range}。以下内容只来自上传文献中可提取的摘要、正文和明确标注段落。\n{problem_lines}\n\n"
        f"## \u4e8c\u3001\u7814\u7a76\u65b9\u6cd5\u6bd4\u8f83\n"
        f"{method_intro}识别到的方法类型：{method_overview}。\n{method_lines}\n\n"
        f"## \u4e09\u3001\u6838\u5fc3\u89c2\u70b9\u4e0e\u8bc1\u636e\n{viewpoint_intro}\n{finding_lines}\n\n"
        f"## \u56db\u3001\u5171\u8bc6\u3001\u5dee\u5f02\u4e0e\u7814\u7a76\u7a7a\u767d\n{gap_lines}"
    )
    markdown = markdown.replace("\u7a7a\u767d", "\u7a7a\u767d\uff08\u7814\u7a76\u4e0d\u8db3\u4e0e\u5c55\u671b\uff09")
    if references:
        markdown += "\n\n## \u4e94\u3001\u53ef\u6838\u9a8c\u7684\u53c2\u8003\u6587\u732e\n" + "\n".join(item["citation"] for item in references)
    return {
        "title": f"{topic}\u6587\u732e\u7efc\u8ff0",
        "topic": topic,
        "markdown": markdown,
        "item_count": len(items),
        "keywords": [keyword for keyword, _ in Counter(k for item in items for k in item.keywords).most_common(12)],
        "themes": [{"name": name, "count": count} for name, count in method_counts.items()],
        "years": years,
        "references": references,
        "unreferenced_sources": [item.filename for item in items if not _citation(item, 1)],
        "document_summaries": [asdict(item) for item in items],
        "engine": "local-rule-engine",
    }


def generate_review(items: list[LiteratureItem], topic: str = "") -> dict:
    _enhance_document_evidence(items)
    local = generate_local_review(items, topic)
    prompt = (
        f"Topic: {local['topic']}\n\n"
        + "\n\n".join(
            f"Title: {item.title}\nAbstract: {item.abstract}\nMethods: {item.methods}\nFindings: {item.findings}\nText: {item.text[:5000]}"
            for item in items
        )
        + "\n\nGenerate Chinese Markdown with sections for research questions, methods, core findings, comparison, and gaps. Use only supplied facts. Do not invent or include references, author names, dates, journals, DOIs, or unsupported methods/findings. Treat each supplied excerpt as source evidence; if evidence is absent, say it was not identified."
    )
    enhanced = generate_review_with_llm(prompt)
    if enhanced and len(enhanced.strip()) >= 120:
        # Never display bibliography entries invented by the model. The only
        # references shown below are assembled from explicitly labeled source
        # metadata extracted from the uploaded documents.
        enhanced = re.split(r"(?im)^\s*#{0,6}\s*(?:可核验的?参考文献|参考文献|references|bibliography)\s*$", enhanced, maxsplit=1)[0].rstrip()
        if local["references"]:
            enhanced += "\n\n## \u53ef\u6838\u9a8c\u7684\u53c2\u8003\u6587\u732e\n" + "\n".join(item["citation"] for item in local["references"])
        local["markdown"] = enhanced
        local["engine"] = "llm-enhanced"
    local["ai"] = llm_status()
    return local


def generate_review_with_llm(prompt: str) -> str | None:
    return generate_llm_review(prompt)


def serialize_items(items: list[LiteratureItem]) -> list[dict]:
    return [asdict(item) for item in items]
