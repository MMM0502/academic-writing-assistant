from __future__ import annotations

from pathlib import Path
from typing import Iterable
import html
import re
import shutil
import subprocess
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


def _pdf_text_legacy(data: bytes) -> str:
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


def _pdf_text(data: bytes) -> str:
    """Extract a PDF text layer without treating PDF objects as document text."""
    pypdf_error = None
    try:
        from pypdf import PdfReader
        import io

        reader = PdfReader(io.BytesIO(data))
        text = clean_text("\n".join(page.extract_text() or "" for page in reader.pages))
        if text:
            return text
    except ImportError:
        pass
    except Exception as exc:
        pypdf_error = exc

    executable = shutil.which("pdftotext")
    if executable:
        try:
            completed = subprocess.run(
                [executable, "-layout", "-", "-"],
                input=data,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
                timeout=45,
            )
            text = clean_text(completed.stdout.decode("utf-8", errors="replace"))
            if text:
                return text
        except (OSError, subprocess.SubprocessError) as exc:
            pypdf_error = pypdf_error or exc

    if pypdf_error:
        raise ValueError(f"PDF text extraction failed: {pypdf_error}") from pypdf_error
    raise ValueError("PDF has no extractable text; it may be a scanned document that requires OCR")


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
    for item in paragraphs[:16]:
        candidate = re.sub(r"^(摘要|abstract|标题|title)\s*[:：]?\s*", "", item, flags=re.I).strip()
        if not (4 <= len(candidate) <= 120):
            continue
        if not re.search(r"[\u4e00-\u9fff]", candidate) and len(re.findall(r"[A-Za-z]", candidate)) < 6:
            continue
        if not re.search(r"[\u4e00-\u9fff]", candidate) and re.search(r"[a-z][A-Z]", candidate):
            continue
        if candidate.startswith(("参考文献", "References")):
            continue
        # PDF first lines often contain the journal masthead, volume/issue,
        # ISSN or running headers. They are source metadata, not the paper
        # title. If no reliable title remains, callers use the filename.
        compact = re.sub(r"\s+", "", candidate)
        letters = re.sub(r"[^A-Za-z]", "", candidate)
        if re.fullmatch(r"(?:[IVXLC]+\.?\s*)?\d+(?:\.\s*\d+)?", candidate) or re.fullmatch(r"[A-Za-z]?\s*[.·-]?\s*\d{1,3}", candidate):
            continue
        if re.match(r"^10\.\d{4,9}/", candidate, re.I):
            continue
        if re.match(r"^(?:19|20)\d{2}\s*年?\s*\d{1,2}\s*月?\b", candidate, re.I):
            continue
        # All-caps running heads and publication names are common in PDF
        # headers. They should never become the paper title.
        if letters and letters.upper() == letters and len(letters) >= 8:
            continue
        if re.search(
            r"学报|学刊|期刊|杂志|journal|forum|public\s*relations|volume|vol\.?\s*\d|no\.?\s*\d|第\s*\d+\s*[卷期]|issn|doi\s*:",
            candidate,
            re.I,
        ) or re.search(r"学报|学刊|期刊|杂志|journal|forum|publicrelations|volume|issn|doi", compact, re.I):
            continue
        if re.search(r"\b(?:大学|学院)\s+(?:学报|journal)\b", candidate, re.I):
            continue
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
