from __future__ import annotations

from pathlib import Path
from typing import Iterable
import html
import re
import zipfile
from xml.etree import ElementTree

SUPPORTED_EXTENSIONS = {".docx", ".pdf", ".txt", ".md"}

_W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
_W = f"{{{_W_NS}}}"

SECTION_PATTERNS: dict[str, str] = {
    "title": r"^(标题|title)\s*[:：]?\s*",
    "abstract": r"^(摘要|abstract|摘\s*要)\s*[:：]?\s*$",
    "keywords": r"^(关键词|keywords?)\s*[:：]?\s*$",
    "introduction": r"^(引言|前言|绪论|背景|introduction)\s*[:：]?\s*$",
    "methods": r"^(方法|研究方法|方法论|methods?|methodology)\s*[:：]?\s*$",
    "results": r"^(结果|实验结果|实验|results?)\s*[:：]?\s*$",
    "discussion": r"^(讨论|discussion)\s*[:：]?\s*$",
    "conclusion": r"^(结论|结语|总结|conclusion|conclusions?)\s*[:：]?\s*$",
    "references": r"^(参考文献|references|bibliography)\s*[:：]?\s*$",
    "acknowledgments": r"^(致谢|acknowledgments?)\s*[:：]?\s*$",
    "appendix": r"^(附录|appendix|appendices)\s*[:：]?\s*$",
}


def clean_text(value: str) -> str:
    value = html.unescape(value or "")
    value = value.replace("\u00a0", " ")
    value = re.sub(r"[ \t]+", " ", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value.strip()


def _docx_read_notes(archive: zipfile.ZipFile, name: str) -> dict[str, str]:
    try:
        xml_data = archive.read(name)
    except KeyError:
        return {}
    try:
        root = ElementTree.fromstring(xml_data)
    except ElementTree.ParseError:
        return {}
    notes: dict[str, str] = {}
    root_tag = root.tag.rsplit("}", 1)[-1]
    child_tag = root_tag[:-1] if root_tag.endswith("s") else root_tag
    for note in root.findall(f"{_W}{child_tag}"):
        note_id = note.get(f"{_W}id", "")
        texts = [t.text for t in note.iter(f"{_W}t") if t.text]
        if note_id and texts:
            notes[note_id] = " ".join(texts).strip()
    return notes


def _docx_element_text(elem) -> str:
    parts: list[str] = []
    for child in elem.iter():
        tag = child.tag.rsplit("}", 1)[-1]
        if tag == "t" and child.text:
            parts.append(child.text)
        elif tag in ("footnoteReference", "endnoteReference"):
            note_id = child.get(f"{_W}id", "")
            if note_id:
                label = "脚注" if tag == "footnoteReference" else "尾注"
                parts.append(f"[{label}占位:{note_id}]")
    return "".join(parts)


def _docx_has_drawing(elem) -> bool:
    for child in elem.iter():
        tag = child.tag.rsplit("}", 1)[-1]
        if tag in ("drawing", "pict", "object"):
            return True
    return False


def _docx_extract_table(tbl_elem) -> str:
    rows: list[str] = []
    for tr in tbl_elem.findall(f"{_W}tr"):
        cells: list[str] = []
        for tc in tr.findall(f"{_W}tc"):
            cell_text = _docx_element_text(tc).strip()
            cells.append(cell_text)
        if cells:
            rows.append(" | ".join(cells))
    return "\n".join(rows)


def _docx_get_heading_level(elem) -> int:
    pPr = elem.find(f"{_W}pPr")
    if pPr is None:
        return 0
    pStyle = pPr.find(f"{_W}pStyle")
    if pStyle is None:
        return 0
    val = pStyle.get(f"{_W}val", "")
    m = re.search(r"[Hh]eading(\d+)", val)
    if m:
        return int(m.group(1))
    if val.lower().startswith("title"):
        return 1
    return 0


def _docx_text(data: bytes) -> str:
    import io

    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        xml_data = archive.read("word/document.xml")
        footnotes = _docx_read_notes(archive, "word/footnotes.xml")
        endnotes = _docx_read_notes(archive, "word/endnotes.xml")
    all_notes = {**footnotes, **endnotes}

    root = ElementTree.fromstring(xml_data)
    body = root.find(f"{_W}body")
    if body is None:
        body = root

    paragraphs: list[str] = []

    for element in body:
        tag = element.tag.rsplit("}", 1)[-1]
        if tag == "p":
            text = _docx_element_text(element).strip()
            has_image = _docx_has_drawing(element)
            heading_level = _docx_get_heading_level(element)
            if has_image:
                if text:
                    paragraphs.append(text)
                paragraphs.append("[图片]")
            elif heading_level > 0 and text:
                paragraphs.append(f"{'#' * heading_level} {text}")
            elif text:
                paragraphs.append(text)
        elif tag == "tbl":
            table_text = _docx_extract_table(element)
            if table_text:
                paragraphs.append(f"[表格]\n{table_text}\n[表格结束]")

    result = "\n".join(paragraphs)
    if all_notes:
        result = _docx_resolve_note_placeholders(result, all_notes)
    return clean_text(result)


def _docx_resolve_note_placeholders(text: str, notes: dict[str, str]) -> str:
    def replacer(match: re.Match) -> str:
        note_id = match.group(2)
        label = match.group(1)
        content = notes.get(note_id, "")
        return f"[{label}：{content}]" if content else ""

    return re.sub(r"\[(脚注|尾注)占位:(\d+)\]", replacer, text)


def _pdf_text(data: bytes) -> str:
    try:
        from pypdf import PdfReader

        import io

        reader = PdfReader(io.BytesIO(data))
        pages_text: list[str] = []
        for page in reader.pages:
            pages_text.append(_pdf_page_text(page))
        return clean_text("\n".join(pages_text))
    except ImportError:
        raw = data.decode("latin-1", errors="ignore")
        strings = re.findall(r"\(([^()]*)\)", raw)
        return clean_text("\n".join(strings))
    except Exception as exc:
        raise ValueError(f"PDF 解析失败：{exc}") from exc


def _pdf_page_text(page) -> str:
    blocks: list[tuple[float, float, str]] = []

    def visitor(text, cm, tm, font_dict, font_size):
        if text and text.strip():
            x = tm[4] if len(tm) > 4 else 0.0
            y = tm[5] if len(tm) > 5 else 0.0
            blocks.append((x, y, text.strip()))

    try:
        page.extract_text(visitor_text=visitor)
    except Exception:
        try:
            return page.extract_text() or ""
        except Exception:
            return ""

    if not blocks:
        try:
            return page.extract_text() or ""
        except Exception:
            return ""

    return _pdf_reconstruct_columns(blocks)


def _pdf_reconstruct_columns(blocks: list[tuple[float, float, str]]) -> str:
    if not blocks:
        return ""
    xs = [b[0] for b in blocks]
    x_min, x_max = min(xs), max(xs)
    x_range = x_max - x_min

    if x_range <= 0:
        return " ".join(b[2] for b in blocks)

    mid = x_min + x_range * 0.5
    left_blocks = [b for b in blocks if b[0] < mid]
    right_blocks = [b for b in blocks if b[0] >= mid]

    if len(left_blocks) > 3 and len(right_blocks) > 3:
        left_sorted = sorted(left_blocks, key=lambda b: (-b[1], b[0]))
        right_sorted = sorted(right_blocks, key=lambda b: (-b[1], b[0]))
        left_text = _pdf_merge_nearby(left_sorted)
        right_text = _pdf_merge_nearby(right_sorted)
        return f"{left_text}\n{right_text}"

    sorted_blocks = sorted(blocks, key=lambda b: (-b[1], b[0]))
    return _pdf_merge_nearby(sorted_blocks)


def _pdf_merge_nearby(sorted_blocks: list[tuple[float, float, str]]) -> str:
    if not sorted_blocks:
        return ""
    lines: list[list[str]] = []
    current_y = sorted_blocks[0][1]
    current_line: list[str] = []

    for x, y, text in sorted_blocks:
        if abs(y - current_y) > 5:
            if current_line:
                lines.append(current_line)
            current_line = [text]
            current_y = y
        else:
            current_line.append(text)
    if current_line:
        lines.append(current_line)

    return "\n".join(" ".join(line) for line in lines)


def extract_text(filename: str, data: bytes) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise ValueError("仅支持 DOCX、PDF、TXT 或 Markdown 文件。")
    if not data:
        raise ValueError("上传文件为空。")
    if suffix == ".docx":
        try:
            return _docx_text(data)
        except (KeyError, zipfile.BadZipFile, ElementTree.ParseError) as exc:
            raise ValueError("DOCX 文件结构无法读取，请确认文件没有损坏。") from exc
    if suffix == ".pdf":
        return _pdf_text(data)
    return clean_text(data.decode("utf-8-sig", errors="replace"))


def split_paragraphs(text: str) -> list[str]:
    return [item.strip() for item in re.split(r"\n\s*\n|\r?\n", text) if item.strip()]


def sentence_list(text: str) -> list[str]:
    return [item.strip() for item in re.split(r"(?<=[。！？.!?])\s*", text) if item.strip()]


def title_from_text(text: str, fallback: str = "未命名学术文稿") -> str:
    paragraphs = split_paragraphs(text)
    for item in paragraphs[:5]:
        candidate = re.sub(r"^(摘要|abstract|标题|title)\s*[:：]?\s*", "", item, flags=re.I)
        candidate = re.sub(r"^#+\s*", "", candidate)
        if 4 <= len(candidate) <= 100 and not candidate.startswith(("参考文献", "References")):
            return candidate
    return fallback


def iter_reference_lines(text: str) -> Iterable[str]:
    in_references = False
    for raw in text.splitlines():
        line = raw.strip()
        if re.match(r"^(参考文献|references|bibliography)\s*[:：]?\s*$", line, re.I):
            in_references = True
            continue
        if in_references and line:
            yield line


def detect_sections(text: str) -> list[dict]:
    lines = text.splitlines()
    sections: list[dict] = []
    current: dict | None = None
    for i, line in enumerate(lines):
        stripped = line.strip()
        for key, pattern in SECTION_PATTERNS.items():
            if re.match(pattern, stripped, re.I):
                if current:
                    current["end"] = i
                current = {"name": key, "label": stripped.rstrip(":："), "start": i, "end": len(lines)}
                sections.append(current)
                break
    return sections


def extract_structure(text: str) -> dict:
    sections = detect_sections(text)
    found = {s["name"] for s in sections}
    expected = {"abstract", "introduction", "methods", "results", "conclusion", "references"}
    missing = expected - found
    return {
        "sections": sections,
        "missing_sections": sorted(missing),
        "has_abstract": "abstract" in found,
        "has_references": "references" in found,
    }
