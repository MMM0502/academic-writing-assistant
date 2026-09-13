import tempfile
import unittest
from pathlib import Path

from app.formatters import format_document
from app.parsers import extract_text, title_from_text
from app.review import build_item, generate_local_review
from app.storage import Store


class ParserTests(unittest.TestCase):
    def test_extract_txt_and_title(self):
        text = "大模型辅助学术写作\n\n摘要：本文研究文稿规整问题。"
        self.assertIn("学术写作", extract_text("demo.txt", text.encode("utf-8")))
        self.assertEqual(title_from_text(text), "大模型辅助学术写作")

    def test_docx_parser_reads_paragraphs(self):
        import io
        import zipfile

        xml = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            "<w:body><w:p><w:r><w:t>第一段</w:t></w:r></w:p>"
            "<w:p><w:r><w:t>第二段</w:t></w:r></w:p></w:body></w:document>"
        )
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w") as archive:
            archive.writestr("word/document.xml", xml)
        self.assertEqual(extract_text("demo.docx", output.getvalue()), "第一段\n第二段")


class FormatterTests(unittest.TestCase):
    def test_formats_references_and_detects_duplicate(self):
        text = (
            "论文标题\n\n正文内容，讨论研究方法。\n\n参考文献\n"
            "张三. 大模型研究. 软件学报, 2024.\n"
            "张三. 大模型研究. 软件学报, 2024."
        )
        result = format_document(text, "gb7714")
        self.assertEqual(result["reference_count"], 2)
        self.assertTrue(any("重复" in warning for warning in result["warnings"]))
        self.assertIn("1. 张三.", result["formatted_text"])

    def test_english_reference_does_not_duplicate_year(self):
        result = format_document(
            "Paper title\n\nBody text.\n\nReferences\nSmith. Large model study. Journal, 2024.",
            "gb7714",
        )
        self.assertEqual(result["references"][0]["source"], "Journal")
        self.assertNotIn("2024, 2024", result["formatted_text"])


class ReviewTests(unittest.TestCase):
    def test_local_review_contains_structure(self):
        items = [
            build_item("软件工程中的智能方法\n\n2024年研究了代码生成和评测方法。", "a.txt"),
            build_item("软件工程中的数据方法\n\n2023年研究了数据治理与质量。", "b.txt"),
        ]
        result = generate_local_review(items, "智能软件工程")
        self.assertEqual(result["item_count"], 2)
        self.assertIn("研究不足与展望", result["markdown"])
        self.assertTrue(result["keywords"])


class StoreTests(unittest.TestCase):
    def test_store_round_trip(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / "test.sqlite3")
            job_id = store.add("format", "测试记录", {"formatted_text": "hello"})
            self.assertEqual(store.get(job_id)["payload"]["formatted_text"], "hello")
            self.assertEqual(len(store.list()), 1)


if __name__ == "__main__":
    unittest.main()
