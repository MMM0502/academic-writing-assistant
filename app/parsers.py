from __future__ import annotations

from pathlib import Path
from typing import Iterable
import html
import re
import zipfile
from xml.etree import ElementTree


SUPPORTED_EXTENSIONS = {".docx", ".pdf", ".txt", ".md"}


def clean_text(value: str) -> str:
    value = html.unescape(value or "")
    value = value.replace("\u00a0", " ")
    value = re.sub(r"[ \t]+", " ", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value.strip()


def _docx_text(data: bytes) -> str:
    with zipfile.ZipFile(__import__("io").BytesIO(data)) as archive:
        xml_data = archive.read("word/document.xml")
    root = ElementTree.fromstring(xml_data)
    paragraphs: list[str] = []
    current: list[str] = []
    for element in root.iter():
        tag = element.tag.rsplit("}", 1)[-1]
        if tag == "t" and element.text:
            current.append(element.text)
        elif tag == "p":
            line = "".join(current).strip()
            if line:
                paragraphs.append(line)
            current = []
    if current:
        paragraphs.append("".join(current).strip())
    return clean_text("\n".join(paragraphs))


def _pdf_text(data: bytes) -> str:
    try:
        from pypdf import PdfReader

        import io

        reader = PdfReader(io.BytesIO(data))
        return clean_text("\n".join(page.extract_text() or "" for page in reader.pages))
    except ImportError:
        # A small fallback keeps the app usable before optional dependencies are installed.
        raw = data.decode("latin-1", errors="ignore")
        strings = re.findall(r"\(([^()]*)\)", raw)
        return clean_text("\n".join(strings))
    except Exception as exc:
        raise ValueError(f"PDF 解析失败：{exc}") from exc


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
        if 4 <= len(candidate) <= 100 and not candidate.startswith(("参考文献", "References")):
            return candidate
    return fallback


def iter_reference_lines(text: str) -> Iterable[str]:
    in_references = False
    for raw in text.splitlines():
        line = raw.strip()
        if re.match(r"^(参考文献|references|bibliography)\s*:?\s*$", line, re.I):
            in_references = True
            continue
        if in_references and line:
            yield line
