import tempfile
import unittest
from pathlib import Path

from app.formatters import format_document
from app.parsers import extract_text, needs_ocr, title_from_text
from app.review import build_item, generate_local_review, generate_review
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


    def test_invalid_pdf_is_not_treated_as_raw_text(self):
        with self.assertRaises(ValueError):
            extract_text("broken.pdf", b"1 0 obj endobj")

    def test_pdf_text_quality_detection(self):
        self.assertTrue(needs_ocr(""))
        self.assertTrue(needs_ocr("P UBLIC RELATIONS FORUM\n" + "r na\n" * 3 + "正文" * 300))
        self.assertFalse(needs_ocr("这是一段正常的论文正文。" * 100))

    def test_pdf_text_quality_detects_spaced_chinese_ocr(self):
        damaged = ("人 工 智 能 与 大 数 据 研 究。" * 30)
        self.assertTrue(needs_ocr(damaged))


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
    def test_keywords_keep_phrases_and_drop_layout_noise(self):
        item = build_item(
            "Paper title\n\nHigher education and environmental science improve education outcomes. "
            "Higher education uses data. ono journal volume 25. Public Relations Forum. pworld",
            "paper.txt",
        )
        self.assertIn("higher education", item.keywords)
        self.assertNotIn("higher", item.keywords)
        self.assertNotIn("ono", item.keywords)
        self.assertNotIn("journal", item.keywords)
        self.assertNotIn("public relations", item.keywords)
        self.assertNotIn("pworld", item.keywords)

    def test_keywords_prefer_authors_keyword_line(self):
        item = build_item(
            "P UBLIC RELATIONS FORUM\n"
            "论文标题\n关键词：精准思政；大数据；路径选择\n"
            "正文包含 prworld 和破碎 OCR 词。",
            "paper.txt",
        )
        self.assertEqual(item.keywords, ["精准思政", "大数据", "路径选择"])

    def test_local_review_contains_structure(self):
        items = [
            build_item("软件工程中的智能方法\n\n2024年研究了代码生成和评测方法。", "a.txt"),
            build_item("软件工程中的数据方法\n\n2023年研究了数据治理与质量。", "b.txt"),
        ]
        result = generate_local_review(items, "智能软件工程")
        self.assertEqual(result["item_count"], 2)
        self.assertIn("研究不足与展望", result["markdown"])
        self.assertTrue(result["keywords"])

    def test_review_entrypoint_falls_back_to_local_engine(self):
        item = build_item("paper title\n\n2024 compared two data analysis methods.", "paper.txt")
        result = generate_review([item], "data analysis")
        self.assertEqual(result["engine"], "local-rule-engine")
        self.assertEqual(result["item_count"], 1)
        self.assertIn("data analysis", result["markdown"])

    def test_reference_uses_detected_metadata_and_marks_missing_fields(self):
        item = build_item(
            "A reliable title\nAuthors: Jane Doe\nJournal: Example Journal\n2024\nAbstract: Findings.",
            "paper.txt",
        )
        result = generate_local_review([item], "reliable methods")
        citation = result["references"][0]["citation"]
        self.assertIn("Jane Doe", citation)
        self.assertIn("Example Journal", citation)
        self.assertIn("2024", citation)
        self.assertNotIn("[作者未识别]", citation)

    def test_review_extracts_methods_and_findings(self):
        item = build_item(
            "A study title\n\n研究方法：采用问卷调查和回归模型。\n结果：结果表明数字化服务显著提升效率。",
            "methods.txt",
        )
        result = generate_local_review([item], "digital services")
        summary = result["document_summaries"][0]
        self.assertIn("问卷", summary["methods"])
        self.assertIn("显著提升效率", summary["findings"])
        self.assertIn("研究方法", result["markdown"])
        self.assertIn("核心观点", result["markdown"])

    def test_review_evidence_keeps_only_complete_source_sentences(self):
        item = build_item(
            "A study title\n\n"
            "摘要：本文采用问卷调查研究数字化服务。结果表明服务效率有所提升。\n"
            "研究方法：问卷调查并采用回归分析\n"
            "参考文献\nOther Author. Cited paper. 2024. DOI: 10.1234/example.2024.1",
            "evidence.txt",
        )
        self.assertEqual(item.abstract, "本文采用问卷调查研究数字化服务。 结果表明服务效率有所提升。")
        self.assertEqual(item.methods, "")
        self.assertEqual(item.doi, "")
        self.assertEqual(item.year, "")
        self.assertEqual(generate_local_review([item], "digital services")["references"], [])

    def test_multiline_abstract_is_collected_until_keywords(self):
        item = build_item(
            "论文标题\n作者：张三\n"
            "摘要：第一句说明研究背景，\n第二句说明研究方法和结论。\n"
            "关键词：人工智能；教育\n正文：这里是正文。",
            "paper.txt",
        )
        self.assertIn("第一句说明研究背景", item.abstract)
        self.assertIn("第二句说明研究方法和结论", item.abstract)
        self.assertNotIn("关键词", item.abstract)

    def test_reference_text_is_not_reported_as_limitation(self):
        item = build_item(
            "论文标题\n摘要：研究内容。\n"
            "研究局限及展望 2024 [J] International Journal of Emerging Markets, 63(2): 1-10.",
            "paper.txt",
        )
        self.assertEqual(item.limitations, "")

    def test_section_heading_is_removed_from_limitation(self):
        item = build_item(
            "论文标题\n摘要：研究内容。\n"
            "6.3 研究局限及展望 在数据获取条件的制约下，本文仅选择部分样本。",
            "paper.txt",
        )
        self.assertNotIn("研究局限及展望", item.limitations)
        self.assertIn("数据获取条件", item.limitations)

    def test_trailing_section_heading_fragment_is_removed(self):
        item = build_item(
            "论文标题\n摘要：研究内容。\n"
            "研究局限及展望：及展望 在撰写过程中受到数据条件制约，本文仅选择部分样本。",
            "paper.txt",
        )
        self.assertFalse(item.limitations.startswith("及展望"))
        self.assertIn("数据条件制约", item.limitations)

    def test_ocr_page_marker_is_removed(self):
        item = build_item(
            "论文标题\n摘要：研究内容。\n"
            "研究局限及展望：===== 第 1 页（OCR）===== RUE ae Brey BESET ER BSE "
            "在数据获取条件的制约下，本文仅选择部分样本。",
            "paper.txt",
        )
        self.assertNotIn("第 1 页", item.limitations)
        self.assertNotIn("OCR", item.limitations)

    def test_review_does_not_guess_author_or_abstract_from_body(self):
        item = build_item(
            "A paper title\n\n张三\nThis paragraph discusses methods but has no sentence ending",
            "paper.txt",
        )
        self.assertEqual(item.authors, "")
        self.assertEqual(item.abstract, "")
        self.assertEqual(item.methods, "")

    def test_document_title_prefers_descriptive_filename(self):
        item = build_item(
            "P UBLIC RELATIONS FORUM\nI. 3\n10.19980/example\nOCR header fragment",
            "_新双高_理念下高职院校产教融合协同育人机制研究__以大数据与会计专业为例.pdf",
        )
        self.assertEqual(item.title, "新双高 理念下高职院校产教融合协同育人机制研究 以大数据与会计专业为例")


class TitleTests(unittest.TestCase):
    def test_title_skips_journal_masthead_and_volume(self):
        text = "高教 学刊\n第25卷 第3期 陕西农林职业技术大学学报 Vo 25 No.\n真正的论文标题\n摘要：本文研究问题。"
        self.assertEqual(title_from_text(text, "uploaded-paper"), "真正的论文标题")

    def test_title_falls_back_when_only_periodical_header_exists(self):
        text = "高教 学刊\n第25卷 第3期 陕西农林职业技术大学学报 Vo 25 No."
        self.assertEqual(title_from_text(text, "uploaded-paper"), "uploaded-paper")

    def test_title_skips_running_head_page_number_and_doi(self):
        text = (
            "P UBLIC RELATIONS FORUM\nI. 3\n"
            "10.19980/j.CN23-1593/G4.2026.26.038\n"
            "大数据背景下高校实践精准思政的研究"
        )
        self.assertEqual(title_from_text(text, "uploaded-paper"), "大数据背景下高校实践精准思政的研究")

    def test_title_skips_short_page_marker(self):
        self.assertEqual(title_from_text("I. 3\n真正的论文标题", "uploaded-paper"), "真正的论文标题")

    def test_title_skips_date_and_journal_header(self):
        self.assertEqual(title_from_text("2026 年 9 月 Jou\n真正的论文标题", "uploaded-paper"), "真正的论文标题")


class StoreTests(unittest.TestCase):
    def test_store_round_trip(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / "test.sqlite3")
            job_id = store.add("format", "测试记录", {"formatted_text": "hello"})
            self.assertEqual(store.get(job_id)["payload"]["formatted_text"], "hello")
            self.assertEqual(len(store.list()), 1)


if __name__ == "__main__":
    unittest.main()
