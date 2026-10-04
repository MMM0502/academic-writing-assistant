from __future__ import annotations

from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import json
import mimetypes
import re
from urllib.parse import parse_qs, urlparse

from .config import settings
from .exporters import download_name, format_result_to_docx, markdown_to_docx, preserve_original_docx, references_to_format, EXPORT_FORMATS, rules_to_export_style
from .formatters import REFERENCE_TYPE_LABELS, STYLE_LABELS, check_citations, format_document, format_references
from .llm import get_status as get_llm_status
from .parsers import extract_text, extract_structure
from .review import build_item, generate_review, serialize_items
from .storage import Store
from . import auth, journals, stats


ROOT = Path(__file__).resolve().parent
store = Store(settings.data_dir / "academic_assistant.sqlite3")
journals.init_builtin_styles(store)


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

    def _get_current_user(self) -> dict | None:
        token = self.headers.get("Authorization", "").removeprefix("Bearer ").strip()
        if not token:
            cookie = self.headers.get("Cookie", "")
            token_match = re.search(r"auth_token=([^;]+)", cookie)
            token = token_match.group(1) if token_match else ""
        return auth.get_current_user(store, token)

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
            user = self._get_current_user()
            user_id = user["user_id"] if user else None
            self.send_payload(HTTPStatus.OK, {"items": store.list(user_id=user_id)})
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
                "export_formats": list(EXPORT_FORMATS.keys()),
            })
        elif parsed.path == "/api/llm-status":
            self.send_payload(HTTPStatus.OK, get_llm_status())
        elif parsed.path == "/api/auth/me":
            user = self._get_current_user()
            if user:
                self.send_payload(HTTPStatus.OK, {"user_id": user["user_id"], "username": user["username"], "role": user["role"]})
            else:
                self.send_payload(HTTPStatus.OK, {"user": None})
        elif parsed.path == "/api/journal-styles":
            self.send_payload(HTTPStatus.OK, {"styles": journals.list_styles(store)})
        elif parsed.path.startswith("/api/journal-styles/"):
            try:
                style_id = int(parsed.path.rsplit("/", 1)[-1])
            except ValueError:
                self.send_payload(HTTPStatus.BAD_REQUEST, {"error": "格式编号无效"})
                return
            style = journals.get_style(store, style_id)
            if not style:
                self.send_payload(HTTPStatus.NOT_FOUND, {"error": "格式不存在"})
            else:
                self.send_payload(HTTPStatus.OK, style)
        elif parsed.path == "/api/stats":
            user = self._get_current_user()
            user_id = user["user_id"] if user else None
            self.send_payload(HTTPStatus.OK, stats.get_stats(store, user_id=user_id))
        elif parsed.path == "/api/comments":
            job_id_str = parse_qs(parsed.query).get("job_id", [""])[0]
            if not job_id_str:
                self.send_payload(HTTPStatus.BAD_REQUEST, {"error": "缺少 job_id"})
                return
            self.send_payload(HTTPStatus.OK, {"comments": store.list_comments(int(job_id_str))})
        elif parsed.path == "/api/shares":
            user = self._get_current_user()
            if not user:
                self.send_payload(HTTPStatus.UNAUTHORIZED, {"error": "请先登录"})
                return
            self.send_payload(HTTPStatus.OK, {"shares": store.list_shares(user["user_id"])})
        elif parsed.path == "/api/users":
            user = self._get_current_user()
            if not user or user["role"] != "teacher":
                self.send_payload(HTTPStatus.FORBIDDEN, {"error": "仅教师可查看用户列表"})
                return
            self.send_payload(HTTPStatus.OK, {"users": store.list_users()})
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
        query = query or {}
        output_format = query.get("format", ["md"])[0].lower()
        mode = query.get("mode", ["rebuild"])[0].lower()
        if output_format == "docx":
            export_style = rules_to_export_style(payload.get("journal_rules")) if payload.get("journal_rules") else None
            if mode == "preserve" and payload.get("source_data"):
                import base64
                original_data = base64.b64decode(payload["source_data"])
                body = preserve_original_docx(original_data, payload, export_style)
            elif payload.get("kind") == "format":
                body = format_result_to_docx(payload, export_style)
            else:
                body = markdown_to_docx(content, payload.get("title", job["title"]), payload.get("style", ""), export_style)
            filename = download_name(job["title"], "docx")
            content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        elif output_format in EXPORT_FORMATS:
            references = payload.get("references", [])
            if not references:
                self.send_payload(HTTPStatus.BAD_REQUEST, {"error": "该记录没有参考文献数据，无法导出为指定格式。"})
                return
            body = references_to_format(references, output_format).encode("utf-8")
            ext = EXPORT_FORMATS[output_format]["extension"]
            filename = download_name(job["title"], ext)
            content_type = EXPORT_FORMATS[output_format]["content_type"]
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

    JSON_POST_PATHS = {
        "/api/auth/register", "/api/auth/login", "/api/auth/logout",
        "/api/journal-styles", "/api/comments", "/api/shares",
    }
    MULTIPART_POST_PATHS = {
        "/api/format", "/api/review", "/api/check-citations", "/api/review/edit",
    }

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path in self.JSON_POST_PATHS:
            try:
                data = self.parse_json_body()
                if parsed.path == "/api/auth/register":
                    self.handle_register(data)
                elif parsed.path == "/api/auth/login":
                    self.handle_login(data)
                elif parsed.path == "/api/auth/logout":
                    self.handle_logout()
                elif parsed.path == "/api/journal-styles":
                    self.handle_create_journal_style(data)
                elif parsed.path == "/api/comments":
                    self.handle_add_comment(data)
                elif parsed.path == "/api/shares":
                    self.handle_create_share(data)
            except ValueError as exc:
                self.send_payload(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            except Exception as exc:
                self.send_payload(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": f"处理失败：{exc}"})
            return
        if parsed.path in self.MULTIPART_POST_PATHS:
            try:
                fields = self.parse_multipart()
                if parsed.path == "/api/format":
                    self.handle_format(fields)
                elif parsed.path == "/api/check-citations":
                    self.handle_check_citations(fields)
                elif parsed.path == "/api/review/edit":
                    self.handle_review_edit(fields)
                else:
                    self.handle_review(fields)
            except ValueError as exc:
                self.send_payload(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            except Exception as exc:
                self.send_payload(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": f"处理失败：{exc}"})
            return
        self.send_payload(HTTPStatus.NOT_FOUND, {"error": "接口不存在"})

    def parse_json_body(self) -> dict:
        content_length = int(self.headers.get("Content-Length", "0"))
        if content_length <= 0:
            return {}
        body = self.rfile.read(content_length)
        if not body:
            return {}
        try:
            data = json.loads(body.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ValueError(f"JSON 解析失败：{exc}")
        if not isinstance(data, dict):
            raise ValueError("请求体必须是 JSON 对象。")
        return data

    def handle_register(self, data: dict) -> None:
        username = data.get("username", "").strip()
        password = data.get("password", "")
        role = data.get("role", "student").strip()
        result = auth.register(store, username, password, role)
        self.send_payload(HTTPStatus.CREATED, result)

    def handle_login(self, data: dict) -> None:
        username = data.get("username", "").strip()
        password = data.get("password", "")
        result = auth.login(store, username, password)
        self.send_payload(HTTPStatus.OK, result)

    def handle_logout(self) -> None:
        token = self.headers.get("Authorization", "").removeprefix("Bearer ").strip()
        if not token:
            cookie = self.headers.get("Cookie", "")
            token_match = re.search(r"auth_token=([^;]+)", cookie)
            token = token_match.group(1) if token_match else ""
        if token:
            auth.logout(store, token)
        self.send_payload(HTTPStatus.OK, {"message": "已登出"})

    def handle_create_journal_style(self, data: dict) -> None:
        user = self._get_current_user()
        created_by = user["user_id"] if user else None
        name = data.get("name", "").strip()
        publisher = data.get("publisher", "").strip()
        rules = data.get("rules", {})
        if not isinstance(rules, dict):
            raise ValueError("格式规则必须是 JSON 对象。")
        style_id = journals.create_custom_style(store, name, rules, publisher=publisher, created_by=created_by)
        style = journals.get_style(store, style_id)
        self.send_payload(HTTPStatus.CREATED, style)

    def handle_add_comment(self, data: dict) -> None:
        user = self._get_current_user()
        if not user:
            self.send_payload(HTTPStatus.UNAUTHORIZED, {"error": "请先登录"})
            return
        job_id = data.get("job_id")
        content = data.get("content", "").strip()
        if not job_id:
            raise ValueError("缺少 job_id。")
        if not content:
            raise ValueError("评论内容不能为空。")
        comment_id = store.add_comment(int(job_id), user["user_id"], content)
        comments = store.list_comments(int(job_id))
        self.send_payload(HTTPStatus.CREATED, {"id": comment_id, "comments": comments})

    def handle_create_share(self, data: dict) -> None:
        user = self._get_current_user()
        if not user:
            self.send_payload(HTTPStatus.UNAUTHORIZED, {"error": "请先登录"})
            return
        job_id = data.get("job_id")
        shared_with_id = data.get("shared_with_id")
        permission = data.get("permission", "view").strip()
        if not job_id:
            raise ValueError("缺少 job_id。")
        if permission not in ("view", "edit"):
            raise ValueError("权限只能是 view 或 edit。")
        share_id = store.create_share(int(job_id), user["user_id"], int(shared_with_id) if shared_with_id else None, permission)
        self.send_payload(HTTPStatus.CREATED, {"id": share_id, "message": "分享已创建"})

    def do_DELETE(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/history":
            user = self._get_current_user()
            user_id = user["user_id"] if user else None
            removed = store.clear(user_id=user_id)
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
        if parsed.path.startswith("/api/journal-styles/"):
            try:
                style_id = int(parsed.path.rsplit("/", 1)[-1])
            except ValueError:
                self.send_payload(HTTPStatus.BAD_REQUEST, {"error": "格式编号无效"})
                return
            if journals.delete_custom_style(store, style_id):
                self.send_payload(HTTPStatus.OK, {"removed": style_id})
            else:
                self.send_payload(HTTPStatus.NOT_FOUND, {"error": "格式不存在或为内置格式，无法删除"})
            return
        if parsed.path.startswith("/api/comments/"):
            try:
                comment_id = int(parsed.path.rsplit("/", 1)[-1])
            except ValueError:
                self.send_payload(HTTPStatus.BAD_REQUEST, {"error": "评论编号无效"})
                return
            if store.delete_comment(comment_id):
                self.send_payload(HTTPStatus.OK, {"removed": comment_id})
            else:
                self.send_payload(HTTPStatus.NOT_FOUND, {"error": "评论不存在"})
            return
        if parsed.path.startswith("/api/shares/"):
            try:
                share_id = int(parsed.path.rsplit("/", 1)[-1])
            except ValueError:
                self.send_payload(HTTPStatus.BAD_REQUEST, {"error": "分享编号无效"})
                return
            if store.delete_share(share_id):
                self.send_payload(HTTPStatus.OK, {"removed": share_id})
            else:
                self.send_payload(HTTPStatus.NOT_FOUND, {"error": "分享不存在"})
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
        journal_style_id = fields.get("journal_style_id", "")
        if journal_style_id:
            try:
                js = journals.get_style(store, int(journal_style_id))
            except ValueError:
                js = None
            if js:
                rules = js["rules"]
                for ref in result["references"]:
                    ref["formatted"] = journals.format_reference_by_rules(ref, rules, ref["index"])
                ref_text = "\n".join(ref["formatted"] for ref in result["references"])
                body_part = result.get("body_text", "")
                result["formatted_text"] = (body_part + "\n\n参考文献\n\n" + ref_text).strip() if body_part else ref_text
                result["style"] = js["name"]
                result["journal_style_id"] = js["id"]
                result["journal_rules"] = rules
        result["source_name"] = uploaded["filename"]
        result["kind"] = "format"
        result["structure"] = extract_structure(text)
        if uploaded["filename"].lower().endswith(".docx"):
            import base64
            result["source_data"] = base64.b64encode(uploaded["data"]).decode("ascii")
            result["preserve_available"] = True
        else:
            result["preserve_available"] = False
        user = self._get_current_user()
        user_id = user["user_id"] if user else None
        job_id = store.add("format", result["title"], result, user_id=user_id)
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
        user = self._get_current_user()
        user_id = user["user_id"] if user else None
        job_id = store.add("review", result["title"], result, user_id=user_id)
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

    def handle_review_edit(self, fields: dict) -> None:
        job_id_str = fields.get("job_id", "")
        if not job_id_str:
            raise ValueError("缺少记录编号。")
        try:
            job_id = int(job_id_str)
        except ValueError:
            raise ValueError("记录编号无效。")
        job = store.get(job_id)
        if not job:
            raise ValueError("记录不存在。")
        payload = job["payload"]
        edited_markdown = fields.get("markdown", "")
        if not edited_markdown.strip():
            raise ValueError("编辑内容不能为空。")
        versions = payload.get("versions", [])
        versions.append({"markdown": payload.get("markdown", ""), "saved_at": payload.get("engine", "unknown")})
        payload["markdown"] = edited_markdown
        payload["versions"] = versions
        payload["engine"] = "user-edited"
        store.delete(job_id)
        new_id = store.add("review", job["title"], payload)
        payload["id"] = new_id
        payload["version_count"] = len(versions) + 1
        self.send_payload(HTTPStatus.OK, payload)


def run_server() -> None:
    server = ThreadingHTTPServer((settings.host, settings.port), Handler)
    print(f"Academic Assistant running at http://{settings.host}:{settings.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
    finally:
        server.server_close()
