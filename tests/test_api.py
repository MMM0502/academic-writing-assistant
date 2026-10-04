from __future__ import annotations

import io
import json
import tempfile
import threading
import unittest
import urllib.request
import urllib.error
import zipfile
from pathlib import Path
from xml.etree import ElementTree

from app import web
from app.storage import Store


def _multipart(fields: dict, files: list[tuple[str, str, bytes]]) -> tuple[bytes, str]:
    boundary = "----AcademicTestBoundary"
    parts: list[bytes] = []
    for key, value in fields.items():
        parts.append(f"--{boundary}\r\n".encode())
        parts.append(f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode())
        parts.append(f"{value}\r\n".encode())
    for field_name, filename, data in files:
        parts.append(f"--{boundary}\r\n".encode())
        parts.append(
            f'Content-Disposition: form-data; name="{field_name}"; filename="{filename}"\r\n'.encode()
        )
        parts.append(b"Content-Type: application/octet-stream\r\n\r\n")
        parts.append(data + b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode())
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


SAMPLE_PAPER = (
    "大模型辅助学术写作研究\n\n"
    "摘要：本文研究文稿规整与文献综述的自动化方法。\n\n"
    "正文内容如[1]所述，相关方法在[2]中有详细讨论。"
    "另一种思路参见(Smith, 2023)。\n\n"
    "参考文献\n"
    "张三. 大模型研究. 软件学报, 2024, 35(2): 12-20.\n"
    "Smith. Large model study. Journal, 2023.\n"
    "李四. 综述方法. 计算机学报, 2022."
).encode("utf-8")


class ApiEndToEndTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        web.store = Store(Path(cls._tmp.name) / "test.sqlite3")
        cls._server = web.ThreadingHTTPServer(("127.0.0.1", 0), web.Handler)
        cls.base_url = f"http://127.0.0.1:{cls._server.server_address[1]}"
        cls._thread = threading.Thread(target=cls._server.serve_forever, daemon=True)
        cls._thread.start()

    @classmethod
    def tearDownClass(cls):
        cls._server.shutdown()
        cls._server.server_close()
        cls._tmp.cleanup()

    def request(self, path: str, method: str = "GET", body: bytes | None = None,
                content_type: str = "application/json") -> tuple[int, dict | bytes]:
        req = urllib.request.Request(self.base_url + path, data=body, method=method)
        req.add_header("Content-Type", content_type)
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                data = response.read()
                status = response.status
        except urllib.error.HTTPError as exc:
            data = exc.read()
            status = exc.code
        if data.startswith(b"{") or data.startswith(b"["):
            return status, json.loads(data.decode("utf-8"))
        return status, data

    def post_multipart(self, path: str, fields: dict, files: list[tuple[str, str, bytes]]) -> tuple[int, dict]:
        body, content_type = _multipart(fields, files)
        return self.request(path, "POST", body, content_type)

    def test_health(self):
        status, payload = self.request("/api/health")
        self.assertEqual(status, 200)
        self.assertEqual(payload["status"], "ok")

    def test_rules(self):
        status, payload = self.request("/api/rules")
        self.assertEqual(status, 200)
        self.assertIn("styles", payload)
        self.assertEqual(len(payload["styles"]), 3)

    def test_format_normal_upload(self):
        status, payload = self.post_multipart(
            "/api/format", {"style": "gb7714"}, [("file", "paper.txt", SAMPLE_PAPER)]
        )
        self.assertEqual(status, 200)
        self.assertGreater(payload["reference_count"], 0)
        self.assertIn("references", payload)
        self.assertIn("citation_check", payload)
        self.assertIn("body_text", payload)
        self.assertTrue(payload["references"][0]["formatted"])

    def test_format_empty_file(self):
        status, payload = self.post_multipart(
            "/api/format", {"style": "gb7714"}, [("file", "empty.txt", b"")]
        )
        self.assertEqual(status, 400)
        self.assertIn("error", payload)

    def test_format_unsupported_extension(self):
        status, payload = self.post_multipart(
            "/api/format", {"style": "gb7714"}, [("file", "data.zip", b"PK\x03\x04")]
        )
        self.assertEqual(status, 400)
        self.assertIn("error", payload)

    def test_format_corrupt_docx(self):
        status, payload = self.post_multipart(
            "/api/format", {"style": "gb7714"}, [("file", "broken.docx", b"not a real docx")]
        )
        self.assertEqual(status, 400)
        self.assertIn("error", payload)

    def test_format_oversized_file(self):
        oversized = b"a" * (web.settings.max_upload_bytes + 1)
        status, payload = self.post_multipart(
            "/api/format", {"style": "gb7714"}, [("file", "big.txt", oversized)]
        )
        self.assertEqual(status, 400)
        self.assertIn("error", payload)

    def test_review_normal_upload(self):
        literature = "智能代码生成方法研究\n\n2024年研究了基于大模型的代码生成与评测。".encode("utf-8")
        status, payload = self.post_multipart(
            "/api/review", {"topic": "智能软件工程"}, [("files", "a.txt", literature)]
        )
        self.assertEqual(status, 200)
        self.assertIn("markdown", payload)
        self.assertGreater(payload["item_count"], 0)

    def test_review_no_files(self):
        status, payload = self.post_multipart("/api/review", {"topic": "测试"}, [])
        self.assertEqual(status, 400)
        self.assertIn("error", payload)

    def test_check_citations(self):
        status, payload = self.post_multipart(
            "/api/check-citations", {"style": "gb7714"}, [("file", "paper.txt", SAMPLE_PAPER)]
        )
        self.assertEqual(status, 200)
        self.assertIn("inline_citations", payload)
        self.assertIn("reference_count", payload)

    def test_history_and_download_flow(self):
        status, payload = self.post_multipart(
            "/api/format", {"style": "gb7714"}, [("file", "paper.txt", SAMPLE_PAPER)]
        )
        self.assertEqual(status, 200)
        job_id = payload["id"]

        status, history = self.request("/api/history")
        self.assertEqual(status, 200)
        self.assertTrue(any(item["id"] == job_id for item in history["items"]))

        status, detail = self.request(f"/api/history/{job_id}")
        self.assertEqual(status, 200)
        self.assertEqual(detail["id"], job_id)

        status, markdown = self.request(f"/api/download/{job_id}?format=md")
        self.assertEqual(status, 200)
        self.assertIsInstance(markdown, bytes)
        self.assertIn("参考文献".encode("utf-8"), markdown)

        status, docx = self.request(f"/api/download/{job_id}?format=docx")
        self.assertEqual(status, 200)
        self.assertIsInstance(docx, bytes)
        self.assertTrue(docx.startswith(b"PK\x03\x04"))
        with zipfile.ZipFile(io.BytesIO(docx)) as archive:
            names = set(archive.namelist())
            self.assertIn("[Content_Types].xml", names)
            self.assertIn("word/document.xml", names)
            self.assertIn("word/styles.xml", names)
            self.assertIn("_rels/.rels", names)
            document_xml = archive.read("word/document.xml")
            ElementTree.fromstring(document_xml)

    def test_download_nonexistent_job(self):
        status, payload = self.request("/api/download/999999?format=md")
        self.assertEqual(status, 404)

    def test_delete_history(self):
        status, payload = self.post_multipart(
            "/api/format", {"style": "gb7714"}, [("file", "paper.txt", SAMPLE_PAPER)]
        )
        self.assertEqual(status, 200)
        job_id = payload["id"]

        status, result = self.request(f"/api/history/{job_id}", method="DELETE")
        self.assertEqual(status, 200)
        self.assertEqual(result["removed"], job_id)

        status, payload = self.request(f"/api/history/{job_id}")
        self.assertEqual(status, 404)

    def test_clear_history(self):
        self.post_multipart(
            "/api/format", {"style": "gb7714"}, [("file", "paper.txt", SAMPLE_PAPER)]
        )
        status, result = self.request("/api/history", method="DELETE")
        self.assertEqual(status, 200)
        self.assertIn("removed", result)

        status, history = self.request("/api/history")
        self.assertEqual(len(history["items"]), 0)

    def test_unknown_endpoint(self):
        status, payload = self.request("/api/nonexistent")
        self.assertEqual(status, 404)

    def test_format_returns_structure(self):
        status, payload = self.post_multipart(
            "/api/format", {"style": "gb7714"}, [("file", "paper.txt", SAMPLE_PAPER)]
        )
        self.assertEqual(status, 200)
        self.assertIn("structure", payload)
        self.assertIn("sections", payload["structure"])
        self.assertIn("missing_sections", payload["structure"])

    def test_format_returns_preserve_available_for_txt(self):
        status, payload = self.post_multipart(
            "/api/format", {"style": "gb7714"}, [("file", "paper.txt", SAMPLE_PAPER)]
        )
        self.assertEqual(status, 200)
        self.assertFalse(payload["preserve_available"])

    def test_format_returns_preserve_available_for_docx(self):
        xml = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            "<w:body><w:p><w:r><w:t>测试论文标题</w:t></w:r></w:p>"
            '<w:p><w:r><w:t>摘要</w:t></w:r></w:p>'
            '<w:p><w:r><w:t>这是足够长的正文内容用于通过长度检查。</w:t></w:r></w:p>'
            '<w:p><w:r><w:t>参考文献</w:t></w:r></w:p>'
            '<w:p><w:r><w:t>1. 作者. 题名. 期刊, 2024.</w:t></w:r></w:p>'
            "</w:body></w:document>"
        )
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w") as archive:
            archive.writestr("word/document.xml", xml)
        docx_data = output.getvalue()

        status, payload = self.post_multipart(
            "/api/format", {"style": "gb7714"}, [("file", "paper.docx", docx_data)]
        )
        self.assertEqual(status, 200)
        self.assertTrue(payload["preserve_available"])

    def test_download_preserve_mode(self):
        xml = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            "<w:body><w:p><w:r><w:t>测试论文标题</w:t></w:r></w:p>"
            '<w:p><w:r><w:t>这是足够长的正文内容用于通过长度检查。</w:t></w:r></w:p>'
            '<w:p><w:r><w:t>参考文献</w:t></w:r></w:p>'
            '<w:p><w:r><w:t>1. 作者. 题名. 期刊, 2024.</w:t></w:r></w:p>'
            "</w:body></w:document>"
        )
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w") as archive:
            archive.writestr("word/document.xml", xml)
        docx_data = output.getvalue()

        status, payload = self.post_multipart(
            "/api/format", {"style": "gb7714"}, [("file", "paper.docx", docx_data)]
        )
        self.assertEqual(status, 200)
        job_id = payload["id"]

        status, docx = self.request(f"/api/download/{job_id}?format=docx&mode=preserve")
        self.assertEqual(status, 200)
        self.assertIsInstance(docx, bytes)
        self.assertTrue(docx.startswith(b"PK\x03\x04"))
        with zipfile.ZipFile(io.BytesIO(docx)) as archive:
            self.assertIn("word/document.xml", archive.namelist())

    def test_llm_status_endpoint(self):
        status, payload = self.request("/api/llm-status")
        self.assertEqual(status, 200)
        self.assertIn("configured", payload)

    def test_rules_include_export_formats(self):
        status, payload = self.request("/api/rules")
        self.assertEqual(status, 200)
        self.assertIn("export_formats", payload)
        self.assertIn("bibtex", payload["export_formats"])

    def test_review_returns_cards(self):
        literature = "智能代码生成方法研究\n\n本文研究代码生成问题。采用大模型方法。结果表明效果良好。".encode("utf-8")
        status, payload = self.post_multipart(
            "/api/review", {"topic": "智能研究"}, [("files", "a.txt", literature)]
        )
        self.assertEqual(status, 200)
        self.assertIn("cards", payload)
        self.assertGreater(len(payload["cards"]), 0)

    def test_review_returns_llm_status(self):
        literature = "研究内容概述\n\n这是关于智能方法的详细研究内容，包含多个方面。".encode("utf-8")
        status, payload = self.post_multipart(
            "/api/review", {"topic": "测试"}, [("files", "a.txt", literature)]
        )
        self.assertEqual(status, 200)
        self.assertIn("llm_status", payload)

    def test_download_bibtex(self):
        status, payload = self.post_multipart(
            "/api/format", {"style": "gb7714"}, [("file", "paper.txt", SAMPLE_PAPER)]
        )
        self.assertEqual(status, 200)
        job_id = payload["id"]
        status, bibtex = self.request(f"/api/download/{job_id}?format=bibtex")
        self.assertEqual(status, 200)
        self.assertIsInstance(bibtex, bytes)
        self.assertIn(b"@article{", bibtex)

    def test_download_ris(self):
        status, payload = self.post_multipart(
            "/api/format", {"style": "gb7714"}, [("file", "paper.txt", SAMPLE_PAPER)]
        )
        self.assertEqual(status, 200)
        job_id = payload["id"]
        status, ris = self.request(f"/api/download/{job_id}?format=ris")
        self.assertEqual(status, 200)
        self.assertIsInstance(ris, bytes)
        self.assertIn(b"TY  -", ris)

    def test_review_edit(self):
        literature = "研究内容\n\n这是足够长的研究内容用于通过检查。".encode("utf-8")
        status, payload = self.post_multipart(
            "/api/review", {"topic": "测试"}, [("files", "a.txt", literature)]
        )
        self.assertEqual(status, 200)
        job_id = payload["id"]

        edited_md = "# 编辑后的综述\n\n这是用户编辑的内容。"
        status, result = self.post_multipart(
            "/api/review/edit", {"job_id": str(job_id), "markdown": edited_md}, []
        )
        self.assertEqual(status, 200)
        self.assertEqual(result["markdown"], edited_md)
        self.assertEqual(result["engine"], "user-edited")


if __name__ == "__main__":
    unittest.main()