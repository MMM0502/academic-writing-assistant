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
    margin_top: int = 1440
    margin_bottom: int = 1440
    margin_left: int = 1440
    margin_right: int = 1440
    heading1_font_ascii: str = "Calibri"
    heading1_font_east: str = "黑体"
    heading1_size: int = 32
    heading1_bold: bool = True
    heading1_alignment: str = "center"
    heading2_font_ascii: str = "Calibri"
    heading2_font_east: str = "黑体"
    heading2_size: int = 28
    heading2_bold: bool = True
    heading3_font_ascii: str = "Calibri"
    heading3_font_east: str = "黑体"
    heading3_size: int = 24
    heading3_bold: bool = True
    ref_font_ascii: str = "Calibri"
    ref_font_east: str = "宋体"
    ref_size: int = 21
    body_alignment: str = "both"
    paragraph_space_before: int = 0
    paragraph_space_after: int = 0
    page_header: str = ""
    page_number_pos: str = "center"
    line_spacing_exact: int = 0
    heading1_alignment: str = "center"
    heading2_alignment: str = "left"
    heading3_alignment: str = "left"
    abstract_max_chars: int = 300


DEFAULT_STYLE = ExportStyle()


def rules_to_export_style(rules: dict) -> ExportStyle:
    if not rules:
        return DEFAULT_STYLE
    cm_to_twip = 567
    pt_to_half_pt = 2
    font_map = {"SimSun": ("Calibri", "宋体"), "SimHei": ("Calibri", "黑体"), "Times New Roman": ("Times New Roman", "宋体")}
    def _fonts(key, default_east="宋体"):
        v = rules.get(key, "SimSun")
        return font_map.get(v, ("Calibri", v))
    def _cm(key, default_cm=2.54):
        try:
            return int(float(rules.get(key, default_cm)) * cm_to_twip)
        except (ValueError, TypeError):
            return int(default_cm * cm_to_twip)
    def _pt(key, default_pt=12):
        try:
            raw = str(rules.get(key, f"{default_pt}pt")).replace("pt", "").strip()
            return int(float(raw) * pt_to_half_pt)
        except (ValueError, TypeError):
            return int(default_pt * pt_to_half_pt)
    def _spacing(key, default_s="1.5"):
        try:
            s = str(rules.get(key, default_s))
            return int(float(s) * 240)
        except (ValueError, TypeError):
            return 360
    def _indent(key):
        v = rules.get(key, "2chars")
        return 480 if v == "2chars" else 0
    body_ascii, body_east = _fonts("font_family")
    body_size = _pt("font_size", 12)
    line_sp = _spacing("line_spacing", "1.5")
    indent = _indent("first_line_indent")
    m_top = _cm("margin_top", 2.54)
    m_bottom = _cm("margin_bottom", 2.54)
    m_left = _cm("margin_left", 3.18)
    m_right = _cm("margin_right", 3.18)
    align_map = {"both": "both", "left": "left", "center": "center", "right": "right"}
    alignment = align_map.get(rules.get("body_alignment", "both"), "both")
    h1_ascii, h1_east = _fonts("heading1_font", "黑体")
    h2_ascii, h2_east = _fonts("heading2_font", "黑体")
    h3_ascii, h3_east = _fonts("heading3_font", "黑体")
    ref_ascii, ref_east = _fonts("ref_font", "宋体")
    exact = 0
    try:
        if rules.get("line_spacing_pt"):
            exact = int(float(rules["line_spacing_pt"]) * 20)
    except (TypeError, ValueError):
        exact = 0
    return ExportStyle(
        body_font_ascii=body_ascii, body_font_east=body_east, body_size=body_size,
        line_spacing=line_sp, line_spacing_exact=exact, first_line_indent=indent,
        margin_top=m_top, margin_bottom=m_bottom, margin_left=m_left, margin_right=m_right,
        page_margin=m_top, body_alignment=alignment,
        heading1_font_ascii=h1_ascii, heading1_font_east=h1_east,
        heading2_font_ascii=h2_ascii, heading2_font_east=h2_east,
        heading3_font_ascii=h3_ascii, heading3_font_east=h3_east,
        heading1_size=_pt("heading1_size", 16), heading2_size=_pt("heading2_size", 14),
        heading3_size=_pt("heading3_size", 12),
        ref_font_ascii=ref_ascii, ref_font_east=ref_east, ref_size=_pt("ref_size", 10.5),
        page_header=rules.get("page_header", ""),
        page_number_pos=rules.get("page_number_pos", "center") or "center",
    )


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
        props = f'<w:pPr><w:ind w:firstLine="{style.first_line_indent}"/><w:jc w:val="{style.body_alignment}"/><w:spacing w:after="{style.body_spacing_after}" w:line="{style.line_spacing}" w:lineRule="auto"/></w:pPr>'
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
    s = export_style
    header_xml = ""
    if s.page_header:
        header_xml = (
            f'<w:headerReference w:type="default" r:id="rIdHeader"/>'
        )
    footer_pgnum = (
        '<w:ftr xmlns:w="{ns}"><w:p><w:pPr><w:jc w:val="{pos}"/></w:pPr>'
        '<w:r><w:fldChar w:fldCharType="begin"/></w:r>'
        '<w:r><w:instrText xml:space="preserve">PAGE</w:instrText></w:r>'
        '<w:r><w:fldChar w:fldCharType="end"/></w:r></w:p></w:ftr>'
    ).format(ns=_W_NS, pos=s.page_number_pos if s.page_number_pos else "center")
    sect_pr = (
        f'<w:sectPr>'
        f'<w:pgSz w:w="{s.page_width}" w:h="{s.page_height}"/>'
        f'<w:pgMar w:top="{s.margin_top}" w:right="{s.margin_right}" w:bottom="{s.margin_bottom}" w:left="{s.margin_left}"/>'
        f'<w:footerReference w:type="default" r:id="rIdFooter"/>'
        f'</w:sectPr>'
    )
    document = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<w:document xmlns:w="{_W_NS}" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<w:body>' + ''.join(document_parts) + sect_pr + '</w:body></w:document>')
    content_types = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
        '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
        '<Override PartName="/word/footer1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/>'
        '</Types>')
    relationships = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
        '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="word/styles.xml"/>'
        '</Relationships>')
    doc_rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rIdFooter" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer" Target="footer1.xml"/>'
        '</Relationships>')
    output = BytesIO()
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", relationships)
        archive.writestr("word/_rels/document.xml.rels", doc_rels)
        archive.writestr("word/document.xml", document)
        archive.writestr("word/styles.xml", _styles_xml(export_style))
        archive.writestr("word/footer1.xml", footer_pgnum)
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

    style_names = _style_id_map(files.get("word/styles.xml", b""))
    _apply_style_to_paragraphs(body, style, style_names)
    _apply_section_margins(root, style)
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


def _style_id_map(styles_xml: bytes) -> dict[str, str]:
    """styleId -> 样式名，用于识别 Word 自带的 Heading 1/2/3。"""
    try:
        root = ElementTree.fromstring(styles_xml)
    except Exception:
        return {}
    mapping: dict[str, str] = {}
    for node in root.findall(f"{_W}style"):
        style_id = node.get(f"{_W}styleId")
        name_node = node.find(f"{_W}name")
        if style_id and name_node is not None:
            mapping[style_id] = name_node.get(f"{_W}val") or ""
    return mapping


_H1_PATTERN = re.compile(r"^(第[一二三四五六七八九十百]+[章节]|[一二三四五六七八九十]+、)")
_H2_PATTERN = re.compile(r"^\d+\.\d+(?!\.)")
_H3_PATTERN = re.compile(r"^(\d+\.\d+\.\d+|（[一二三四五六七八九十]+）)")
_CAPTION_PATTERN = re.compile(r"^[图表]\s*\d")
_SPECIAL_HEADINGS = {"摘要", "目录", "参考文献", "致谢", "附录", "abstract", "references", "contents"}


def _classify_paragraph(text: str, style_name: str) -> str:
    name = (style_name or "").strip().lower()
    if name.startswith("heading 1") or name.startswith("标题 1") or name == "标题1":
        return "heading1"
    if name.startswith("heading 2") or name.startswith("标题 2") or name == "标题2":
        return "heading2"
    if name.startswith("heading 3") or name.startswith("标题 3") or name == "标题3":
        return "heading3"
    stripped = text.strip()
    if not stripped:
        return "empty"
    if stripped.lower() in _SPECIAL_HEADINGS:
        return "heading1"
    if _H1_PATTERN.match(stripped):
        return "heading1"
    if _H3_PATTERN.match(stripped):
        return "heading3"
    if _H2_PATTERN.match(stripped):
        return "heading2"
    if _CAPTION_PATTERN.match(stripped):
        return "caption"
    return "body"


def _sub(parent, tag: str):
    node = parent.find(tag)
    if node is None:
        node = ElementTree.SubElement(parent, tag)
    return node


def _role_fonts(role: str, style: ExportStyle) -> tuple[str, str, int, bool]:
    if role == "heading1":
        return style.heading1_font_ascii, style.heading1_font_east, style.heading1_size, style.heading1_bold
    if role == "heading2":
        return style.heading2_font_ascii, style.heading2_font_east, style.heading2_size, style.heading2_bold
    if role == "heading3":
        return style.heading3_font_ascii, style.heading3_font_east, style.heading3_size, style.heading3_bold
    if role == "reference":
        return style.ref_font_ascii, style.ref_font_east, style.ref_size, False
    return style.body_font_ascii, style.body_font_east, style.body_size, False


def _apply_run_format(run, role: str, style: ExportStyle) -> None:
    ascii_name, east_name, size, bold = _role_fonts(role, style)
    rpr = run.find(f"{_W}rPr")
    if rpr is None:
        rpr = ElementTree.Element(f"{_W}rPr")
        run.insert(0, rpr)
    fonts = _sub(rpr, f"{_W}rFonts")
    fonts.set(f"{_W}ascii", ascii_name)
    fonts.set(f"{_W}hAnsi", ascii_name)
    fonts.set(f"{_W}eastAsia", east_name)
    for tag in ("sz", "szCs"):
        node = _sub(rpr, f"{_W}{tag}")
        node.set(f"{_W}val", str(size))
    if bold:
        node = _sub(rpr, f"{_W}b")
        node.set(f"{_W}val", "1")
    else:
        existing = rpr.find(f"{_W}b")
        if existing is not None:
            rpr.remove(existing)


def _apply_paragraph_format(p, role: str, style: ExportStyle) -> None:
    ppr = p.find(f"{_W}pPr")
    if ppr is None:
        ppr = ElementTree.Element(f"{_W}pPr")
        p.insert(0, ppr)

    jc = _sub(ppr, f"{_W}jc")
    if role == "heading1":
        jc.set(f"{_W}val", "center")
    elif role in ("heading2", "heading3"):
        jc.set(f"{_W}val", "left")
    elif role == "caption":
        jc.set(f"{_W}val", "center")
    else:
        jc.set(f"{_W}val", style.body_alignment or "both")

    spacing = _sub(ppr, f"{_W}spacing")
    if style.line_spacing_exact:
        spacing.set(f"{_W}line", str(style.line_spacing_exact))
        spacing.set(f"{_W}lineRule", "exact")
    else:
        spacing.set(f"{_W}line", str(style.line_spacing))
        spacing.set(f"{_W}lineRule", "auto")
    if role in ("heading1", "heading2", "heading3"):
        spacing.set(f"{_W}before", "240")
        spacing.set(f"{_W}after", "120")

    ind = _sub(ppr, f"{_W}ind")
    if role == "reference":
        ind.set(f"{_W}left", str(style.reference_hanging_indent))
        ind.set(f"{_W}hanging", str(style.reference_hanging_indent))
        ind.attrib.pop(f"{_W}firstLine", None)
        ind.attrib.pop(f"{_W}firstLineChars", None)
    elif role.startswith("heading") or role == "caption":
        ind.set(f"{_W}firstLine", "0")
        ind.set(f"{_W}firstLineChars", "0")
    else:
        ind.set(f"{_W}firstLine", str(style.first_line_indent))
        ind.set(f"{_W}firstLineChars", "200" if style.first_line_indent else "0")

    # 标题层级用大纲级别，导航窗格和自动目录才能识别
    outline = ppr.find(f"{_W}outlineLvl")
    if role in ("heading1", "heading2", "heading3"):
        if outline is None:
            outline = ElementTree.SubElement(ppr, f"{_W}outlineLvl")
        outline.set(f"{_W}val", {"heading1": "0", "heading2": "1", "heading3": "2"}[role])
    elif outline is not None:
        ppr.remove(outline)


def _apply_section_margins(root, style: ExportStyle) -> None:
    for sect in root.iter(f"{_W}sectPr"):
        pgsz = _sub(sect, f"{_W}pgSz")
        pgsz.set(f"{_W}w", str(style.page_width))
        pgsz.set(f"{_W}h", str(style.page_height))
        pgmar = _sub(sect, f"{_W}pgMar")
        pgmar.set(f"{_W}top", str(style.margin_top))
        pgmar.set(f"{_W}bottom", str(style.margin_bottom))
        pgmar.set(f"{_W}left", str(style.margin_left))
        pgmar.set(f"{_W}right", str(style.margin_right))


def _apply_style_to_paragraphs(body, style: ExportStyle, style_names: dict[str, str] | None = None) -> None:
    """按规则重写每个段落的字体、字号、对齐、缩进、行距。表格内段落保持原样。"""
    style_names = style_names or {}
    table_paragraphs = {id(p) for table in body.iter(f"{_W}tbl") for p in table.iter(f"{_W}p")}
    in_reference_section = False
    # 封面区：从开头到第一个标题（或第一段长正文）之间的段落保持原样，
    # 否则封面上的“硕士学位论文 / 作者 / 学号”会被套成宋体小四正文。
    cover_mode = True
    cover_skipped = 0
    styled = 0

    for p in body.iter(f"{_W}p"):
        if id(p) in table_paragraphs:
            continue
        text = "".join(node.text or "" for node in p.iter(f"{_W}t")).strip()
        ppr = p.find(f"{_W}pPr")
        style_id = None
        if ppr is not None:
            pstyle = ppr.find(f"{_W}pStyle")
            if pstyle is not None:
                style_id = pstyle.get(f"{_W}val")
        style_name = style_names.get(style_id, "") if style_id else ""

        role = _classify_paragraph(text, style_name)
        if role == "empty":
            continue
        if cover_mode:
            if role.startswith("heading") or len(text) > 80:
                cover_mode = False
            else:
                cover_skipped += 1
                continue
        if role == "heading1" and text.strip() in ("参考文献", "References", "references"):
            in_reference_section = True
            role = "heading1"
        elif role == "heading1" and in_reference_section:
            in_reference_section = False
        elif in_reference_section:
            role = "reference"

        _apply_paragraph_format(p, role, style)
        for run in p.iter(f"{_W}r"):
            if not "".join(node.text or "" for node in run.iter(f"{_W}t")).strip():
                continue
            _apply_run_format(run, role, style)
        styled += 1

    return {"cover_skipped": cover_skipped, "styled": styled}


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


_STYLE_NAME_ROLES = {
    "normal": "body",
    "正文": "body",
    "heading 1": "heading1",
    "标题 1": "heading1",
    "标题1": "heading1",
    "heading 2": "heading2",
    "标题 2": "heading2",
    "标题2": "heading2",
    "heading 3": "heading3",
    "标题 3": "heading3",
    "标题3": "heading3",
}


def _write_rpr(parent, ascii_name: str, east_name: str, size: int, bold: bool) -> None:
    rpr = parent.find(f"{_W}rPr")
    if rpr is None:
        rpr = ElementTree.SubElement(parent, f"{_W}rPr")
    fonts = _sub(rpr, f"{_W}rFonts")
    fonts.set(f"{_W}ascii", ascii_name)
    fonts.set(f"{_W}hAnsi", ascii_name)
    fonts.set(f"{_W}eastAsia", east_name)
    for tag in ("sz", "szCs"):
        node = _sub(rpr, f"{_W}{tag}")
        node.set(f"{_W}val", str(size))
    if bold:
        node = _sub(rpr, f"{_W}b")
        node.set(f"{_W}val", "1")
    else:
        existing = rpr.find(f"{_W}b")
        if existing is not None:
            rpr.remove(existing)


def _write_ppr(parent, style: ExportStyle, role: str) -> None:
    ppr = parent.find(f"{_W}pPr")
    if ppr is None:
        ppr = ElementTree.SubElement(parent, f"{_W}pPr")
    spacing = _sub(ppr, f"{_W}spacing")
    if style.line_spacing_exact:
        spacing.set(f"{_W}line", str(style.line_spacing_exact))
        spacing.set(f"{_W}lineRule", "exact")
    else:
        spacing.set(f"{_W}line", str(style.line_spacing))
        spacing.set(f"{_W}lineRule", "auto")
    ind = _sub(ppr, f"{_W}ind")
    if role == "body":
        ind.set(f"{_W}firstLine", str(style.first_line_indent))
        ind.set(f"{_W}firstLineChars", "200" if style.first_line_indent else "0")
    else:
        ind.set(f"{_W}firstLine", "0")
        ind.set(f"{_W}firstLineChars", "0")
    if role in ("heading1", "heading2", "heading3"):
        jc = _sub(ppr, f"{_W}jc")
        jc.set(f"{_W}val", "center" if role == "heading1" else "left")
        spacing.set(f"{_W}before", "240")
        spacing.set(f"{_W}after", "120")


def _merge_styles_xml(original_xml: bytes, style: ExportStyle) -> str:
    """把规则写进 styles.xml：文档默认、Normal、Heading 1-3 一起改，
    这样用户接着打字、自动目录、导航窗格都会沿用新格式。"""
    try:
        root = ElementTree.fromstring(original_xml)
    except ElementTree.ParseError:
        return _styles_xml(style)

    # 1) 文档默认字体与行距
    doc_defaults = root.find(f"{_W}docDefaults")
    if doc_defaults is not None:
        rpr_default = doc_defaults.find(f"{_W}rPrDefault")
        if rpr_default is None:
            rpr_default = ElementTree.SubElement(doc_defaults, f"{_W}rPrDefault")
        rpr = rpr_default.find(f"{_W}rPr")
        if rpr is None:
            rpr = ElementTree.SubElement(rpr_default, f"{_W}rPr")
        fonts = _sub(rpr, f"{_W}rFonts")
        fonts.set(f"{_W}ascii", style.body_font_ascii)
        fonts.set(f"{_W}hAnsi", style.body_font_ascii)
        fonts.set(f"{_W}eastAsia", style.body_font_east)
        for tag in ("sz", "szCs"):
            node = _sub(rpr, f"{_W}{tag}")
            node.set(f"{_W}val", str(style.body_size))

    # 2) 具名样式
    for node in root.findall(f"{_W}style"):
        name_node = node.find(f"{_W}name")
        if name_node is None:
            continue
        role = _STYLE_NAME_ROLES.get((name_node.get(f"{_W}val") or "").strip().lower())
        if not role:
            continue
        if role == "body":
            _write_rpr(node, style.body_font_ascii, style.body_font_east, style.body_size, False)
        elif role == "heading1":
            _write_rpr(node, style.heading1_font_ascii, style.heading1_font_east, style.heading1_size, style.heading1_bold)
        elif role == "heading2":
            _write_rpr(node, style.heading2_font_ascii, style.heading2_font_east, style.heading2_size, style.heading2_bold)
        else:
            _write_rpr(node, style.heading3_font_ascii, style.heading3_font_east, style.heading3_size, style.heading3_bold)
        _write_ppr(node, style, role)

    return '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n' + ElementTree.tostring(root, encoding="unicode")


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
        formatted = str(ref.get("formatted") or "").strip()
        if not formatted:
            index = ref.get("index", "")
            parts = [f"[{index}]", ref.get("authors", ""), ref.get("title", ""), ref.get("source", "")]
            if ref.get("year"):
                parts.append(str(ref["year"]))
            formatted = ". ".join(part for part in parts if part) + "."
        lines.append(formatted)
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
