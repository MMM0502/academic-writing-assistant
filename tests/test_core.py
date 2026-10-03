import io
import tempfile
import unittest
import zipfile
from pathlib import Path

from app.exporters import ExportStyle, format_result_to_docx, preserve_original_docx
from app.formatters import format_document, parse_reference, split_authors
from app.parsers import detect_sections, extract_structure, extract_text, title_from_text
from app.review import build_item, generate_local_review
from app.storage import Store


_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def _make_docx(document_xml: str, extra_files: dict | None = None) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr("word/document.xml", document_xml)
        if extra_files:
            for name, data in extra_files.items():
                archive.writestr(name, data)
    return output.getvalue()


class ParserTests(unittest.TestCase):
    def test_extract_txt_and_title(self):
        text = "大模型辅助学术写作\n\n摘要：本文研究文稿规整问题。"
        self.assertIn("学术写作", extract_text("demo.txt", text.encode("utf-8")))
        self.assertEqual(title_from_text(text), "大模型辅助学术写作")

    def test_docx_parser_reads_paragraphs(self):
        xml = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'<w:document xmlns:w="{_W}">'
            "<w:body><w:p><w:r><w:t>第一段</w:t></w:r></w:p>"
            "<w:p><w:r><w:t>第二段</w:t></w:r></w:p></w:body></w:document>"
        )
        self.assertEqual(extract_text("demo.docx", _make_docx(xml)), "第一段\n第二段")

    def test_docx_extracts_table(self):
        xml = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'<w:document xmlns:w="{_W}"><w:body>'
            "<w:tbl><w:tr><w:tc><w:p><w:r><w:t>A1</w:t></w:r></w:p></w:tc>"
            "<w:tc><w:p><w:r><w:t>B1</w:t></w:r></w:p></w:tc></w:tr>"
            "<w:tr><w:tc><w:p><w:r><w:t>A2</w:t></w:r></w:p></w:tc>"
            "<w:tc><w:p><w:r><w:t>B2</w:t></w:r></w:p></w:tc></w:tr></w:tbl>"
            "</w:body></w:document>"
        )
        result = extract_text("demo.docx", _make_docx(xml))
        self.assertIn("[表格]", result)
        self.assertIn("A1 | B1", result)
        self.assertIn("A2 | B2", result)
        self.assertIn("[表格结束]", result)

    def test_docx_detects_image(self):
        xml = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'<w:document xmlns:w="{_W}"><w:body>'
            "<w:p><w:r><w:drawing/></w:r></w:p>"
            "</w:body></w:document>"
        )
        result = extract_text("demo.docx", _make_docx(xml))
        self.assertIn("[图片]", result)

    def test_docx_reads_footnotes(self):
        doc_xml = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'<w:document xmlns:w="{_W}"><w:body>'
            '<w:p><w:r><w:t>正文</w:t></w:r>'
            f'<w:r><w:rPr></w:rPr><w:footnoteReference w:id="1"/></w:r></w:p>'
            "</w:body></w:document>"
        )
        fn_xml = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'<w:footnotes xmlns:w="{_W}">'
            f'<w:footnote w:id="1"><w:p><w:r><w:t>这是脚注内容</w:t></w:r></w:p></w:footnote>'
            "</w:footnotes>"
        )
        result = extract_text("demo.docx", _make_docx(doc_xml, {"word/footnotes.xml": fn_xml}))
        self.assertIn("正文", result)
        self.assertIn("脚注", result)
        self.assertIn("这是脚注内容", result)

    def test_docx_heading_style(self):
        xml = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'<w:document xmlns:w="{_W}"><w:body>'
            '<w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>引言</w:t></w:r></w:p>'
            '<w:p><w:r><w:t>正文内容</w:t></w:r></w:p>'
            "</w:body></w:document>"
        )
        result = extract_text("demo.docx", _make_docx(xml))
        self.assertIn("# 引言", result)

    def test_detect_sections(self):
        text = (
            "标题\n\n摘要\n\n这是摘要内容。\n\n引言\n\n这是引言。\n\n"
            "方法\n\n这是方法。\n\n结论\n\n这是结论。\n\n参考文献\n\n[1] 文献"
        )
        sections = detect_sections(text)
        names = [s["name"] for s in sections]
        self.assertIn("abstract", names)
        self.assertIn("introduction", names)
        self.assertIn("methods", names)
        self.assertIn("conclusion", names)
        self.assertIn("references", names)

    def test_extract_structure_missing(self):
        text = "标题\n\n正文内容但没有标准章节。"
        structure = extract_structure(text)
        self.assertIn("abstract", structure["missing_sections"])
        self.assertIn("references", structure["missing_sections"])
        self.assertFalse(structure["has_abstract"])


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

    def test_layered_parsing_extracts_volume_issue_pages(self):
        raw = "Smith J. Deep learning. Nature, 2024, 35(2): 12-20."
        ref = parse_reference(raw, 1, "gb7714")
        self.assertEqual(ref.year, "2024")
        self.assertEqual(ref.volume, "35")
        self.assertEqual(ref.issue, "2")
        self.assertEqual(ref.pages, "12-20")

    def test_layered_parsing_extracts_doi(self):
        raw = "Smith J. Deep learning. Nature, 2024. DOI: 10.1038/nature12345."
        ref = parse_reference(raw, 1, "gb7714")
        self.assertEqual(ref.doi, "10.1038/nature12345")

    def test_split_authors_chinese(self):
        authors = split_authors("张三, 李四, 王五")
        self.assertEqual(len(authors), 3)
        self.assertEqual(authors[0], "张三")

    def test_split_authors_english_with_et_al(self):
        authors = split_authors("Smith, J., Lee, K., et al.")
        self.assertGreater(len(authors), 1)
        self.assertNotIn("et al", authors[0])

    def test_split_authors_semicolon(self):
        authors = split_authors("Smith J; Lee K; Wang X")
        self.assertEqual(len(authors), 3)

    def test_reference_has_errors_field(self):
        ref = parse_reference("无年份文献", 1, "gb7714")
        self.assertIsInstance(ref.errors, list)
        self.assertTrue(any(e["field"] == "year" for e in ref.errors))

    def test_reference_has_author_list(self):
        ref = parse_reference("张三, 李四. 研究. 期刊, 2024.", 1, "gb7714")
        self.assertIsInstance(ref.author_list, list)
        self.assertGreater(len(ref.author_list), 0)

    def test_confidence_levels(self):
        ref_good = parse_reference("Smith J. Title. Journal, 2024, 35(2): 12-20.", 1, "gb7714")
        self.assertIn(ref_good.confidence, ("high", "medium"))
        ref_bad = parse_reference("???", 1, "gb7714")
        self.assertEqual(ref_bad.confidence, "low")

    def test_apa7_format_includes_year_in_parentheses(self):
        ref = parse_reference("Smith J. Title. Journal, 2024.", 1, "apa7")
        self.assertIn("(2024)", ref.formatted)

    def test_ieee_format_includes_bracket_number(self):
        ref = parse_reference("Smith J. Title. Journal, 2024.", 1, "ieee")
        self.assertIn("[1]", ref.formatted)


class ExporterTests(unittest.TestCase):
    def _sample_result(self) -> dict:
        return {
            "title": "测试论文",
            "body_text": "这是正文内容。",
            "references": [
                {"formatted": "1. 张三. 研究. 期刊, 2024."},
                {"formatted": "2. 李四. 方法. 学报, 2023."},
            ],
            "kind": "format",
        }

    def test_format_result_to_docx_produces_valid_docx(self):
        result = self._sample_result()
        docx = format_result_to_docx(result)
        self.assertTrue(docx.startswith(b"PK\x03\x04"))
        with zipfile.ZipFile(io.BytesIO(docx)) as archive:
            self.assertIn("word/document.xml", archive.namelist())
            self.assertIn("word/styles.xml", archive.namelist())

    def test_custom_export_style(self):
        style = ExportStyle(title_size=36, body_size=28, line_spacing=400)
        result = self._sample_result()
        docx = format_result_to_docx(result, style)
        with zipfile.ZipFile(io.BytesIO(docx)) as archive:
            doc_xml = archive.read("word/document.xml").decode("utf-8")
            self.assertIn('w:val="36"', doc_xml)
            self.assertIn('w:line="400"', doc_xml)

    def test_preserve_original_docx_keeps_content(self):
        doc_xml = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'<w:document xmlns:w="{_W}"><w:body>'
            '<w:p><w:r><w:t>原始正文</w:t></w:r></w:p>'
            '<w:p><w:r><w:t>参考文献</w:t></w:r></w:p>'
            '<w:p><w:r><w:t>[1] 旧文献</w:t></w:r></w:p>'
            "</w:body></w:document>"
        )
        original = _make_docx(doc_xml)
        result = self._sample_result()
        docx = preserve_original_docx(original, result)
        self.assertTrue(docx.startswith(b"PK\x03\x04"))
        with zipfile.ZipFile(io.BytesIO(docx)) as archive:
            self.assertIn("word/document.xml", archive.namelist())
            content = archive.read("word/document.xml").decode("utf-8")
            self.assertIn("原始正文", content)

    def test_preserve_falls_back_on_invalid_docx(self):
        result = self._sample_result()
        docx = preserve_original_docx(b"not a docx", result)
        self.assertTrue(docx.startswith(b"PK\x03\x04"))


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
