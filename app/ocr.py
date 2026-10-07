from __future__ import annotations

import io
import os
import shutil


def _tesseract_command() -> str:
    configured = os.getenv("TESSERACT_CMD", "").strip()
    if configured:
        return configured
    return shutil.which("tesseract") or r"C:\Program Files\Tesseract-OCR\tesseract.exe"


def ocr_pdf(data: bytes) -> str:
    """Render each PDF page and recognize Chinese/English text with Tesseract."""
    try:
        try:
            import pymupdf as fitz  # New PyMuPDF import name
        except ImportError:
            import fitz  # Older PyMuPDF releases
        import pytesseract
        from PIL import Image, ImageOps
    except ImportError as exc:
        raise RuntimeError(
            "OCR 依赖未安装，请运行：python -m pip install pymupdf pytesseract Pillow"
        ) from exc

    command = _tesseract_command()
    if not os.path.exists(command) and not shutil.which(command):
        raise RuntimeError(
            "找不到 Tesseract，请安装 Tesseract OCR，或设置 TESSERACT_CMD 指向 tesseract.exe"
        )
    pytesseract.pytesseract.tesseract_cmd = command

    language = os.getenv("OCR_LANG", "chi_sim+eng")
    dpi = max(150, int(os.getenv("OCR_DPI", "300")))
    psm = os.getenv("OCR_PSM", "3")
    preprocess = os.getenv("OCR_PREPROCESS", "auto").lower() != "off"
    max_pages = int(os.getenv("OCR_MAX_PAGES", "0"))
    document = fitz.open(stream=data, filetype="pdf")
    pages = []
    try:
        page_count = len(document) if max_pages <= 0 else min(len(document), max_pages)
        matrix = fitz.Matrix(dpi / 72, dpi / 72)
        for index in range(page_count):
            pixmap = document[index].get_pixmap(matrix=matrix, alpha=False)
            image = Image.open(io.BytesIO(pixmap.tobytes("png")))
            if preprocess:
                image = ImageOps.autocontrast(ImageOps.grayscale(image))
            text = pytesseract.image_to_string(
                image,
                lang=language,
                config=f"--oem 1 --psm {psm}",
            )
            pages.append(f"\n===== 第 {index + 1} 页（OCR）=====\n{text}")
    finally:
        document.close()
    return "\n".join(pages).strip()
