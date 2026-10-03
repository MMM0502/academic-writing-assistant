from __future__ import annotations

from html import escape
from io import BytesIO
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile
import re


_REFERENCE_HEADINGS = {"参考文献", "references", "bibliography", "references:"}


def _run_xml(text: str, kind: str = "body") -> str:
    text = escape(text, quote=False)
    fonts = '<w:rFonts w:ascii="Calibri" w:hAnsi="Calibri" w:eastAsia="宋体"/>'
    if kind == "title":
        run_props = fonts + '<w:b/><w:sz w:val="32"/><w:szCs w:val="32"/>'
    elif kind == "heading":
        run_props = fonts + '<w:b/><w:color w:val="167C80"/><w:sz w:val="28"/><w:szCs w:val="28"/>'
    else:
        run_props = fonts + '<w:sz w:val="24"/><w:szCs w:val="24"/>'
    return f'<w:r><w:rPr>{run_props}</w:rPr><w:t xml:space="preserve">{text}</w:t></w:r>'


def _paragraph_xml(text: str, kind: str = "body") -> str:
    if kind == "title":
        props = '<w:pPr><w:jc w:val="center"/><w:spacing w:after="260"/></w:pPr>'
    elif kind == "heading":
        props = '<w:pPr><w:keepNext/><w:spacing w:before="260" w:after="140"/></w:pPr>'
    elif kind == "reference":
        props = '<w:pPr><w:ind w:left="420" w:hanging="420"/><w:spacing w:after="100" w:line="300" w:lineRule="auto"/></w:pPr>'
    else:
        props = '<w:pPr><w:ind w:firstLine="480"/><w:spacing w:after="160" w:line="360" w:lineRule="auto"/></w:pPr>'
    return f'<w:p>{props}{_run_xml(text, kind)}</w:p>'


def _styles_xml() -> str:
    return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri" w:eastAsia="宋体"/><w:sz w:val="24"/><w:szCs w:val="24"/></w:rPr></w:rPrDefault></w:docDefaults>
  <w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/><w:qFormat/><w:pPr><w:spacing w:line="360" w:lineRule="auto"/></w:pPr></w:style>
</w:styles>'''


def _is_reference_heading(line: str) -> bool:
    return line.strip().lower().rstrip(":：") in {h.rstrip(":：") for h in _REFERENCE_HEADINGS}


def _looks_like_reference_entry(line: str) -> bool:
    return bool(re.match(r"^\s*(?:\[\d+\]|\d+[.)、])\s+", line))


def markdown_to_docx(markdown: str, title: str = "", style: str = "") -> bytes:
    """Generate a newly formatted DOCX from processed text, never the uploaded source file."""
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
            document_parts.append(_paragraph_xml("参考文献", "heading"))
        elif markdown_heading:
            document_parts.append(_paragraph_xml(line, "heading"))
        elif first_content and title and line == title:
            document_parts.append(_paragraph_xml(line, "title"))
        elif first_content and not title:
            document_parts.append(_paragraph_xml(line, "title"))
        elif in_references or _looks_like_reference_entry(line):
            document_parts.append(_paragraph_xml(line, "reference"))
        else:
            document_parts.append(_paragraph_xml(line, "body"))
        first_content = False

    return _build_docx(document_parts)


def format_result_to_docx(result: dict) -> bytes:
    """Build a normalized Word document from processed fields, never from the source file."""
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

    parts = [_paragraph_xml(title, "title")]
    for item in body_paragraphs:
        if item == title:
            continue
        if _is_reference_heading(item):
            continue
        if _looks_like_reference_entry(item) and reference_lines:
            continue
        parts.append(_paragraph_xml(item, "body"))

    if reference_lines:
        parts.append(_paragraph_xml("参考文献", "heading"))
        for line in reference_lines:
            parts.append(_paragraph_xml(line, "reference"))

    return _build_docx(parts)


def _build_docx(document_parts: list[str]) -> bytes:
    document = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        '<w:body>' + ''.join(document_parts) + '<w:sectPr><w:pgSz w:w="11906" w:h="16838"/>'
        '<w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440"/>'
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
        archive.writestr("word/styles.xml", _styles_xml())
    return output.getvalue()


def download_name(title: str, extension: str) -> str:
    safe = Path(title or "academic-result").stem
    safe = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", safe).strip(" .") or "academic-result"
    return f"{safe}.{extension}"
