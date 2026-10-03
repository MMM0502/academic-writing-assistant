from __future__ import annotations

from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import json
import mimetypes
import re
from urllib.parse import parse_qs, urlparse

from .config import settings
from .exporters import download_name, format_result_to_docx, markdown_to_docx
from .formatters import REFERENCE_TYPE_LABELS, STYLE_LABELS, check_citations, format_document, format_references
from .parsers import extract_text
from .review import build_item, generate_review, serialize_items
from .storage import Store


ROOT = Path(__file__).resolve().parent
store = Store(settings.data_dir / "academic_assistant.sqlite3")


def json_bytes(payload: dict) -> bytes:
    return json.dumps(payload, ensure_ascii=False).encode("utf-8")


def safe_filename(name: str) -> str:
    name = Path(name or "download.md").name
    return re.sub(r"[^0-9A-Za-z\u4e00-\u9fff._-]", "_", name)


class Handler(BaseHTTPRequestHandler):
    server_version = "AcademicAssistant/1.0"

    def log_message(self, fmt: str, *args) -> None:
        print(f"[{self.log_date_time_string()}] {fmt % args}")

    def send_payload(self, status: int, payload: dict, content_type: str = "application/json; charset=utf-8"):
        body = json_bytes(payload) if content_type.startswith("application/json") else payload
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self.serve_file(ROOT / "templates" / "index.html", "text/html; charset=utf-8")
        elif parsed.path.startswith("/static/"):
            relative = parsed.path.removeprefix("/static/").replace("/", "\\")
            target = (ROOT / "static" / relative).resolve()
            if str(target).startswith(str((ROOT / "static").resolve())) and target.is_file():
                self.serve_file(target, mimetypes.guess_type(str(target))[0] or "application/octet-stream")
            else:
                self.send_payload(HTTPStatus.NOT_FOUND, {"error": "资源不存在"})
        elif parsed.path == "/api/history":
            self.send_payload(HTTPStatus.OK, {"items": store.list()})
        elif parsed.path.startswith("/api/history/"):
            try:
                job_id = int(parsed.path.rsplit("/", 1)[-1])
            except ValueError:
                self.send_payload(HTTPStatus.BAD_REQUEST, {"error": "记录编号无效"})
                return
            job = store.get(job_id)
            if not job:
                self.send_payload(HTTPStatus.NOT_FOUND, {"error": "记录不存在"})
            else:
                self.send_payload(HTTPStatus.OK, job)
        elif parsed.path.startswith("/api/download/"):
            self.download_job(parsed.path.rsplit("/", 1)[-1], parse_qs(parsed.query))
        elif parsed.path == "/api/health":
            self.send_payload(HTTPStatus.OK, {"status": "ok", "service": "academic-assistant"})
        elif parsed.path == "/api/rules":
            self.send_payload(HTTPStatus.OK, {
                "styles": [{"code": code, "label": label} for code, label in STYLE_LABELS.items()],
                "reference_types": REFERENCE_TYPE_LABELS,
            })
        else:
            self.send_payload(HTTPStatus.NOT_FOUND, {"error": "接口不存在"})

    def serve_file(self, path: Path, content_type: str) -> None:
        try:
            body = path.read_bytes()
        except FileNotFoundError:
            self.send_payload(HTTPStatus.NOT_FOUND, {"error": "页面不存在"})
            return
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def download_job(self, value: str, query: dict[str, list[str]] | None = None) -> None:
        try:
            job = store.get(int(value))
        except ValueError:
            job = None
        if not job:
            self.send_payload(HTTPStatus.NOT_FOUND, {"error": "记录不存在"})
            return
        payload = job["payload"]
        content = payload.get("formatted_text") or payload.get("markdown") or ""
        output_format = (query or {}).get("format", ["md"])[0].lower()
        if output_format == "docx":
            body = (format_result_to_docx(payload) if payload.get("kind") == "format" else markdown_to_docx(content, payload.get("title", job["title"]), payload.get("style", "")))
            filename = download_name(job["title"], "docx")
            content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        else:
            output_format = "md"
            body = content.encode("utf-8")
            filename = download_name(job["title"], "md")
            content_type = "text/markdown; charset=utf-8"
        encoded_filename = __import__("urllib.parse", fromlist=["quote"]).quote(filename)
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header(
            "Content-Disposition",
            f'attachment; filename="academic-result.{output_format}"; filename*=UTF-8\'\'{encoded_filename}',
        )
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path not in {"/api/format", "/api/review", "/api/check-citations"}:
            self.send_payload(HTTPStatus.NOT_FOUND, {"error": "接口不存在"})
            return
        try:
            fields = self.parse_multipart()
            if parsed.path == "/api/format":
                self.handle_format(fields)
            elif parsed.path == "/api/check-citations":
                self.handle_check_citations(fields)
            else:
                self.handle_review(fields)
        except ValueError as exc:
            self.send_payload(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
        except Exception as exc:
            self.send_payload(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": f"处理失败：{exc}"})

    def do_DELETE(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/history":
            removed = store.clear()
            self.send_payload(HTTPStatus.OK, {"removed": removed})
            return
        if parsed.path.startswith("/api/history/"):
            try:
                job_id = int(parsed.path.rsplit("/", 1)[-1])
            except ValueError:
                self.send_payload(HTTPStatus.BAD_REQUEST, {"error": "记录编号无效"})
                return
            if store.delete(job_id):
                self.send_payload(HTTPStatus.OK, {"removed": job_id})
            else:
                self.send_payload(HTTPStatus.NOT_FOUND, {"error": "记录不存在"})
            return
        self.send_payload(HTTPStatus.NOT_FOUND, {"error": "接口不存在"})

    def parse_multipart(self) -> dict:
        content_length = int(self.headers.get("Content-Length", "0"))
        if content_length <= 0:
            raise ValueError("请求内容为空。")
        if content_length > settings.max_upload_bytes * 10:
            raise ValueError("请求过大，请减少文件数量或压缩文件。")
        body = self.rfile.read(content_length)
        content_type = self.headers.get("Content-Type", "")
        if "multipart/form-data" not in content_type:
            raise ValueError("请求必须使用 multipart/form-data。")
        boundary_match = re.search(r"boundary=([^;]+)", content_type)
        if not boundary_match:
            raise ValueError("无法解析上传请求的边界。")
        boundary = boundary_match.group(1).strip().strip('"').encode("utf-8")
        separator = b"--" + boundary
        result: dict = {"files": []}
        for raw_part in body.split(separator):
            part = raw_part.strip(b"\r\n")
            if not part or part.startswith(b"--"):
                continue
            header_end = part.find(b"\r\n\r\n")
            if header_end == -1:
                continue
            header_block = part[:header_end].decode("utf-8", errors="replace")
            content = part[header_end + 4:]
            if content.endswith(b"\r\n"):
                content = content[:-2]
            disp = re.search(
                r'Content-Disposition: form-data; name="([^"]+)"(?:; filename="([^"]*)")?',
                header_block,
            )
            if not disp:
                continue
            name, filename = disp.group(1), disp.group(2)
            if filename is not None:
                if len(content) > settings.max_upload_bytes:
                    raise ValueError("单个文件不能超过 12 MB。")
                if not filename:
                    continue
                result["files"].append(
                    {"field": name, "filename": safe_filename(filename), "data": content}
                )
            else:
                result[name] = content.decode("utf-8", errors="replace")
        return result

    def handle_format(self, fields: dict) -> None:
        files = fields["files"]
        if not files:
            raise ValueError("请上传一篇 DOCX、PDF 或 TXT 文稿。")
        uploaded = files[0]
        text = extract_text(uploaded["filename"], uploaded["data"])
        if len(text) < 20:
            raise ValueError("文件中可识别的正文过少，请检查文件内容。")
        style = fields.get("style", "gb7714")
        result = format_document(text, style)
        result["source_name"] = uploaded["filename"]
        result["kind"] = "format"
        job_id = store.add("format", result["title"], result)
        result["id"] = job_id
        self.send_payload(HTTPStatus.OK, result)

    def handle_review(self, fields: dict) -> None:
        if not fields["files"]:
            raise ValueError("请至少上传一篇文献。")
        items = []
        skipped = []
        for uploaded in fields["files"]:
            try:
                text = extract_text(uploaded["filename"], uploaded["data"])
                if len(text) < 20:
                    raise ValueError("有效文本过少")
                items.append(build_item(text, uploaded["filename"]))
            except ValueError as exc:
                skipped.append(f"{uploaded['filename']}：{exc}")
        if not items:
            raise ValueError("没有可处理的文献。")
        result = generate_review(items, fields.get("topic", ""))
        result["source_names"] = [item["filename"] for item in fields["files"]]
        result["skipped"] = skipped
        result["kind"] = "review"
        job_id = store.add("review", result["title"], result)
        result["id"] = job_id
        result["items"] = serialize_items(items)
        self.send_payload(HTTPStatus.OK, result)

    def handle_check_citations(self, fields: dict) -> None:
        files = fields["files"]
        if not files:
            raise ValueError("请上传一篇需要检查引用的文稿。")
        uploaded = files[0]
        text = extract_text(uploaded["filename"], uploaded["data"])
        if len(text) < 20:
            raise ValueError("文件中可识别的正文过少，请检查文件内容。")
        style = fields.get("style", "gb7714")
        document = format_document(text, style)
        result = document["citation_check"]
        result["title"] = document["title"]
        result["reference_count"] = document["reference_count"]
        result["references"] = [
            {"index": ref["index"], "title": ref["title"], "year": ref["year"], "authors": ref["authors"]}
            for ref in document["references"]
        ]
        self.send_payload(HTTPStatus.OK, result)


def run_server() -> None:
    server = ThreadingHTTPServer((settings.host, settings.port), Handler)
    print(f"Academic Assistant running at http://{settings.host}:{settings.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
    finally:
        server.server_close()
