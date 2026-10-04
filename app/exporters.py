from __future__ import annotations

from dataclasses import dataclass
from html import escape
from io import BytesIO
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile
from xml.etree import ElementTree
import re


_W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
_W = f"{{{_W_NS}}}"

_REFERENCE_HEADINGS = {"参考文献", "references", "bibliography", "references:"}

ElementTree.register_namespace("w", _W_NS)


@dataclass
class ExportStyle:
    title_font_ascii: str = "Calibri"
    title_font_east: str = "宋体"
    title_size: int = 32
    body_font_ascii: str = "Calibri"
    body_font_east: str = "宋体"
    body_size: int = 24
    heading_color: str = "167C80"
    heading_size: int = 28
    line_spacing: int = 360
    first_line_indent: int = 480
    reference_hanging_indent: int = 420
    reference_line_spacing: int = 300
    reference_spacing_after: int = 100
    body_spacing_after: int = 160
    page_margin: int = 1440
    page_width: int = 11906
    page_height: int = 16838


DEFAULT_STYLE = ExportStyle()


def _run_xml(text: str, kind: str = "body", style: ExportStyle = None) -> str:
    style = style or DEFAULT_STYLE
    text = escape(text, quote=False)
    if kind == "title":
        fonts = f'<w:rFonts w:ascii="{style.title_font_ascii}" w:hAnsi="{style.title_font_ascii}" w:eastAsia="{style.title_font_east}"/>'
        run_props = fonts + f'<w:b/><w:sz w:val="{style.title_size}"/><w:szCs w:val="{style.title_size}"/>'
    elif kind == "heading":
        fonts = f'<w:rFonts w:ascii="{style.title_font_ascii}" w:hAnsi="{style.title_font_ascii}" w:eastAsia="{style.title_font_east}"/>'
        run_props = fonts + f'<w:b/><w:color w:val="{style.heading_color}"/><w:sz w:val="{style.heading_size}"/><w:szCs w:val="{style.heading_size}"/>'
    else:
        fonts = f'<w:rFonts w:ascii="{style.body_font_ascii}" w:hAnsi="{style.body_font_ascii}" w:eastAsia="{style.body_font_east}"/>'
        run_props = fonts + f'<w:sz w:val="{style.body_size}"/><w:szCs w:val="{style.body_size}"/>'
    return f'<w:r><w:rPr>{run_props}</w:rPr><w:t xml:space="preserve">{text}</w:t></w:r>'


def _paragraph_xml(text: str, kind: str = "body", style: ExportStyle = None) -> str:
    style = style or DEFAULT_STYLE
    if kind == "title":
        props = f'<w:pPr><w:jc w:val="center"/><w:spacing w:after="260"/></w:pPr>'
    elif kind == "heading":
        props = '<w:pPr><w:keepNext/><w:spacing w:before="260" w:after="140"/></w:pPr>'
    elif kind == "reference":
        props = f'<w:pPr><w:ind w:left="{style.reference_hanging_indent}" w:hanging="{style.reference_hanging_indent}"/><w:spacing w:after="{style.reference_spacing_after}" w:line="{style.reference_line_spacing}" w:lineRule="auto"/></w:pPr>'
    else:
        props = f'<w:pPr><w:ind w:firstLine="{style.first_line_indent}"/><w:spacing w:after="{style.body_spacing_after}" w:line="{style.line_spacing}" w:lineRule="auto"/></w:pPr>'
    return f'<w:p>{props}{_run_xml(text, kind, style)}</w:p>'


def _styles_xml(style: ExportStyle = None) -> str:
    style = style or DEFAULT_STYLE
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="{_W_NS}">
  <w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="{style.body_font_ascii}" w:hAnsi="{style.body_font_ascii}" w:eastAsia="{style.body_font_east}"/><w:sz w:val="{style.body_size}"/><w:szCs w:val="{style.body_size}"/></w:rPr></w:rPrDefault></w:docDefaults>
  <w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/><w:qFormat/><w:pPr><w:spacing w:line="{style.line_spacing}" w:lineRule="auto"/></w:pPr></w:style>
</w:styles>'''


def _is_reference_heading(line: str) -> bool:
    return line.strip().lower().rstrip(":：") in {h.rstrip(":：") for h in _REFERENCE_HEADINGS}


def _looks_like_reference_entry(line: str) -> bool:
    return bool(re.match(r"^\s*(?:\[\d+\]|\d+[.)、])\s+", line))


def markdown_to_docx(markdown: str, title: str = "", style_code: str = "", export_style: ExportStyle = None) -> bytes:
    lines = []
    for raw_line in markdown.replace("\r\n", "\n").split("\n"):
        line = raw_line.strip()
        if not line:
            continue
        line = re.sub(r"\*\*(.*?)\*\*", r"\1", line)
        line = re.sub(r"`(.*?)`", r"\1", line)
        heading = line.startswith("#")
        if heading:
            line = re.sub(r"^#+\s*", "", line)
        lines.append((line, heading))
    if not lines:
        lines = [(title or "暂无可下载内容", False)]

    document_parts = []
    first_content = True
    in_references = False
    for line, markdown_heading in lines:
        if _is_reference_heading(line):
            if in_references:
                continue
            in_references = True
            document_parts.append(_paragraph_xml("参考文献", "heading", export_style))
        elif markdown_heading:
            document_parts.append(_paragraph_xml(line, "heading", export_style))
        elif first_content and title and line == title:
            document_parts.append(_paragraph_xml(line, "title", export_style))
        elif first_content and not title:
            document_parts.append(_paragraph_xml(line, "title", export_style))
        elif in_references or _looks_like_reference_entry(line):
            document_parts.append(_paragraph_xml(line, "reference", export_style))
        else:
            document_parts.append(_paragraph_xml(line, "body", export_style))
        first_content = False

    return _build_docx(document_parts, export_style)


def format_result_to_docx(result: dict, export_style: ExportStyle = None) -> bytes:
    title = str(result.get("title") or "学术文稿")
    body_text = str(result.get("body_text") or "")
    if not body_text:
        formatted = str(result.get("formatted_text") or "")
        body_text = re.split(r"\n\s*参考文献\s*\n", formatted, maxsplit=1, flags=re.I)[0]

    body_paragraphs = [item.strip() for item in re.split(r"\n\s*\n", body_text) if item.strip()]

    reference_items = result.get("references", []) or []
    reference_lines: list[str] = []
    for new_index, item in enumerate(reference_items, start=1):
        formatted_line = str(item.get("formatted") or "").strip()
        if not formatted_line:
            continue
        formatted_line = re.sub(r"^\s*\[\d+\]\s*", f"[{new_index}] ", formatted_line)
        formatted_line = re.sub(r"^\s*\d+[.)、]\s*", f"{new_index}. ", formatted_line)
        reference_lines.append(formatted_line)

    parts = [_paragraph_xml(title, "title", export_style)]
    for item in body_paragraphs:
        if item == title:
            continue
        if _is_reference_heading(item):
            continue
        if _looks_like_reference_entry(item) and reference_lines:
            continue
        parts.append(_paragraph_xml(item, "body", export_style))

    if reference_lines:
        parts.append(_paragraph_xml("参考文献", "heading", export_style))
        for line in reference_lines:
            parts.append(_paragraph_xml(line, "reference", export_style))

    return _build_docx(parts, export_style)


def _build_docx(document_parts: list[str], export_style: ExportStyle = None) -> bytes:
    export_style = export_style or DEFAULT_STYLE
    document = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<w:document xmlns:w="{_W_NS}">'
        '<w:body>' + ''.join(document_parts) +
        f'<w:sectPr><w:pgSz w:w="{export_style.page_width}" w:h="{export_style.page_height}"/>'
        f'<w:pgMar w:top="{export_style.page_margin}" w:right="{export_style.page_margin}" w:bottom="{export_style.page_margin}" w:left="{export_style.page_margin}"/>'
        '</w:sectPr></w:body></w:document>')
    content_types = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
        '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
        '</Types>')
    relationships = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
        '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="word/styles.xml"/>'
        '</Relationships>')
    output = BytesIO()
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", relationships)
        archive.writestr("word/document.xml", document)
        archive.writestr("word/styles.xml", _styles_xml(export_style))
    return output.getvalue()


def preserve_original_docx(original_data: bytes, result: dict, export_style: ExportStyle = None) -> bytes:
    """保留原稿导出：在原始 DOCX 基础上修改段落样式，保留图片/表格/页眉页脚等内容。"""
    export_style = export_style or DEFAULT_STYLE
    try:
        return _do_preserve_original_docx(original_data, result, export_style)
    except Exception:
        return format_result_to_docx(result, export_style)


def _do_preserve_original_docx(original_data: bytes, result: dict, style: ExportStyle) -> bytes:
    with ZipFile(BytesIO(original_data)) as archive:
        names = archive.namelist()
        files: dict[str, bytes] = {name: archive.read(name) for name in names}

    if "word/document.xml" not in files:
        raise ValueError("缺少 word/document.xml")

    document_xml = files["word/document.xml"]
    root = ElementTree.fromstring(document_xml)
    body = root.find(f"{_W}body")
    if body is None:
        raise ValueError("缺少 body 元素")

    _apply_style_to_paragraphs(body, style)
    _replace_references_in_place(body, result, style)

    if "word/styles.xml" in files:
        files["word/styles.xml"] = _merge_styles_xml(files["word/styles.xml"], style).encode("utf-8")
    else:
        files["word/styles.xml"] = _styles_xml(style).encode("utf-8")

    files["word/document.xml"] = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        + ElementTree.tostring(root, encoding="unicode")
    ).encode("utf-8")

    output = BytesIO()
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        for name, data in files.items():
            archive.writestr(name, data)
    return output.getvalue()


def _apply_style_to_paragraphs(body, style: ExportStyle) -> None:
    """为每个段落添加首行缩进和行距样式。"""
    for p in body.iter(f"{_W}p"):
        pPr = p.find(f"{_W}pPr")
        if pPr is None:
            pPr = ElementTree.SubElement(p, f"{_W}pPr")
            p.insert(0, pPr)

        spacing = pPr.find(f"{_W}spacing")
        if spacing is None:
            spacing = ElementTree.SubElement(pPr, f"{_W}spacing")
        if spacing.get(f"{_W}line") is None:
            spacing.set(f"{_W}line", str(style.line_spacing))
            spacing.set(f"{_W}lineRule", "auto")

        ind = pPr.find(f"{_W}ind")
        if ind is None:
            ind = ElementTree.SubElement(pPr, f"{_W}ind")
        if ind.get(f"{_W}firstLine") is None:
            ind.set(f"{_W}firstLine", str(style.first_line_indent))


def _replace_references_in_place(body, result: dict, style: ExportStyle) -> None:
    """在原文档中定位参考文献段落并替换为规整后的内容。"""
    reference_items = result.get("references", []) or []
    if not reference_items:
        return

    ref_lines: list[str] = []
    for new_index, item in enumerate(reference_items, start=1):
        formatted_line = str(item.get("formatted") or "").strip()
        if not formatted_line:
            continue
        formatted_line = re.sub(r"^\s*\[\d+\]\s*", f"[{new_index}] ", formatted_line)
        formatted_line = re.sub(r"^\s*\d+[.)、]\s*", f"{new_index}. ", formatted_line)
        ref_lines.append(formatted_line)

    if not ref_lines:
        return

    paragraphs = [child for child in body if child.tag == f"{_W}p"]
    ref_start_idx = None
    for i, p in enumerate(paragraphs):
        text = _extract_paragraph_text(p).strip()
        if _is_reference_heading(text):
            ref_start_idx = i
            break

    if ref_start_idx is None:
        return

    for p in paragraphs[ref_start_idx + 1:]:
        body.remove(p)

    heading_p = paragraphs[ref_start_idx]
    _clear_paragraph_runs(heading_p)
    _add_run_to_paragraph(heading_p, "参考文献", "heading", style)

    for line in ref_lines:
        new_p = ElementTree.SubElement(body, f"{_W}p")
        pPr = ElementTree.SubElement(new_p, f"{_W}pPr")
        ind = ElementTree.SubElement(pPr, f"{_W}ind")
        ind.set(f"{_W}left", str(style.reference_hanging_indent))
        ind.set(f"{_W}hanging", str(style.reference_hanging_indent))
        spacing = ElementTree.SubElement(pPr, f"{_W}spacing")
        spacing.set(f"{_W}after", str(style.reference_spacing_after))
        spacing.set(f"{_W}line", str(style.reference_line_spacing))
        spacing.set(f"{_W}lineRule", "auto")
        _add_run_to_paragraph(new_p, line, "reference", style)


def _extract_paragraph_text(p) -> str:
    parts = [t.text for t in p.iter(f"{_W}t") if t.text]
    return "".join(parts)


def _clear_paragraph_runs(p) -> None:
    for child in list(p):
        tag = child.tag.rsplit("}", 1)[-1]
        if tag != "pPr":
            p.remove(child)


def _add_run_to_paragraph(p, text: str, kind: str, style: ExportStyle) -> None:
    run_xml = _run_xml(text, kind, style)
    run_xml = run_xml.replace("<w:r>", f'<w:r xmlns:w="{_W_NS}">', 1)
    run_elem = ElementTree.fromstring(run_xml)
    p.append(run_elem)


def _merge_styles_xml(original_xml: bytes, style: ExportStyle) -> str:
    """在原 styles.xml 基础上注入默认行距。"""
    try:
        root = ElementTree.fromstring(original_xml)
        doc_defaults = root.find(f"{_W}docDefaults")
        if doc_defaults is not None:
            rpr_default = doc_defaults.find(f"{_W}rPrDefault")
            if rpr_default is not None:
                rpr = rpr_default.find(f"{_W}rPr")
                if rpr is not None:
                    spacing = rpr.find(f"{_W}spacing")
                    if spacing is None:
                        spacing = ElementTree.SubElement(rpr, f"{_W}spacing")
                    if spacing.get(f"{_W}line") is None:
                        spacing.set(f"{_W}line", str(style.line_spacing))
                        spacing.set(f"{_W}lineRule", "auto")
        return '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n' + ElementTree.tostring(root, encoding="unicode")
    except ElementTree.ParseError:
        return _styles_xml(style)


def download_name(title: str, extension: str) -> str:
    safe = Path(title or "academic-result").stem
    safe = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", safe).strip(" .") or "academic-result"
    return f"{safe}.{extension}"


def _escape_bibtex(value: str) -> str:
    return value.replace("&", "\\&").replace("%", "\\%").replace("_", "\\_").replace("#", "\\#")


def references_to_bibtex(references: list[dict]) -> str:
    entries = []
    for ref in references:
        authors = ref.get("authors", "")
        title = ref.get("title", "")
        year = ref.get("year", "").replace("n.d.", "")
        source = ref.get("source", "")
        volume = ref.get("volume", "")
        issue = ref.get("issue", "")
        pages = ref.get("pages", "")
        doi = ref.get("doi", "")
        ref_type = ref.get("reference_type", "journal")
        key = re.sub(r"[^a-zA-Z]", "", authors.split(",")[0])[:8] + (year or "nd")
        entry_type = {"journal": "article", "conference": "inproceedings", "thesis": "phdthesis",
                      "book": "book", "web": "misc", "patent": "misc", "report": "techreport"}.get(ref_type, "article")
        lines = [f"@{entry_type}{{{key},"]
        if authors:
            lines.append(f"  author = {{{_escape_bibtex(authors)}}},")
        if title:
            lines.append(f"  title = {{{_escape_bibtex(title)}}},")
        if source:
            field = "journal" if entry_type == "article" else "booktitle" if entry_type == "inproceedings" else "publisher"
            lines.append(f"  {field} = {{{_escape_bibtex(source)}}},")
        if year:
            lines.append(f"  year = {{{year}}},")
        if volume:
            lines.append(f"  volume = {{{volume}}},")
        if issue:
            lines.append(f"  number = {{{issue}}},")
        if pages:
            lines.append(f"  pages = {{{pages}}},")
        if doi:
            lines.append(f"  doi = {{{doi}}},")
        lines.append("}")
        entries.append("\n".join(lines))
    return "\n\n".join(entries)


def references_to_ris(references: list[dict]) -> str:
    entries = []
    type_map = {"journal": "JOUR", "conference": "CONF", "thesis": "THES",
                "book": "BOOK", "web": "ELEC", "patent": "PATENT", "report": "RPRT"}
    for ref in references:
        lines = [f"TY  - {type_map.get(ref.get('reference_type', 'journal'), 'JOUR')}"]
        authors = ref.get("authors", "")
        if authors:
            for author in authors.split(";"):
                author = author.strip()
                if author:
                    lines.append(f"AU  - {author}")
        if ref.get("title"):
            lines.append(f"TI  - {ref['title']}")
        if ref.get("source"):
            lines.append(f"JO  - {ref['source']}")
        year = ref.get("year", "").replace("n.d.", "")
        if year:
            lines.append(f"PY  - {year}")
        if ref.get("volume"):
            lines.append(f"VL  - {ref['volume']}")
        if ref.get("issue"):
            lines.append(f"IS  - {ref['issue']}")
        if ref.get("pages"):
            lines.append(f"SP  - {ref['pages']}")
        if ref.get("doi"):
            lines.append(f"DO  - {ref['doi']}")
        if ref.get("url"):
            lines.append(f"UR  - {ref['url']}")
        lines.append("ER  -")
        entries.append("\n".join(lines))
    return "\n\n".join(entries)


def references_to_endnote(references: list[dict]) -> str:
    type_map = {"journal": "0", "conference": "1", "thesis": "3",
                "book": "4", "web": "5", "patent": "6", "report": "7"}
    records = []
    for ref in references:
        lines = [f"TY  - {type_map.get(ref.get('reference_type', 'journal'), '0')}"]
        authors = ref.get("authors", "")
        if authors:
            lines.append(f"AU  - {authors}")
        if ref.get("title"):
            lines.append(f"TI  - {ref['title']}")
        if ref.get("source"):
            lines.append(f"SO  - {ref['source']}")
        year = ref.get("year", "").replace("n.d.", "")
        if year:
            lines.append(f"PY  - {year}")
        if ref.get("volume"):
            lines.append(f"VL  - {ref['volume']}")
        if ref.get("issue"):
            lines.append(f"IS  - {ref['issue']}")
        if ref.get("pages"):
            lines.append(f"SP  - {ref['pages']}")
        if ref.get("doi"):
            lines.append(f"DO  - {ref['doi']}")
        lines.append("ER  -")
        records.append("\n".join(lines))
    return "\n\n".join(records)


def references_to_plaintext(references: list[dict]) -> str:
    lines = []
    for ref in references:
        index = ref.get("index", "")
        authors = ref.get("authors", "")
        title = ref.get("title", "")
        source = ref.get("source", "")
        year = ref.get("year", "")
        volume = ref.get("volume", "")
        issue = ref.get("issue", "")
        pages = ref.get("pages", "")
        doi = ref.get("doi", "")
        parts = [f"[{index}]"]
        if authors:
            parts.append(authors)
        if title:
            parts.append(title)
        if source:
            parts.append(source)
        if volume:
            parts.append(f"Vol.{volume}")
        if issue:
            parts.append(f"No.{issue}")
        if pages:
            parts.append(f"pp.{pages}")
        if year:
            parts.append(year)
        if doi:
            parts.append(f"DOI:{doi}")
        lines.append(". ".join(parts) + ".")
    return "\n".join(lines)


EXPORT_FORMATS = {
    "bibtex": {"extension": "bib", "content_type": "application/x-bibtex"},
    "ris": {"extension": "ris", "content_type": "application/x-research-info-systems"},
    "endnote": {"extension": "enw", "content_type": "application/x-endnote-refer"},
    "txt": {"extension": "txt", "content_type": "text/plain; charset=utf-8"},
}


def references_to_format(references: list[dict], fmt: str) -> str:
    if fmt == "bibtex":
        return references_to_bibtex(references)
    if fmt == "ris":
        return references_to_ris(references)
    if fmt == "endnote":
        return references_to_endnote(references)
    if fmt == "txt":
        return references_to_plaintext(references)
    raise ValueError(f"不支持的导出格式：{fmt}")
