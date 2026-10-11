import unittest

from app.citation_engine import render_references, render_reference


class CitationEngineTests(unittest.TestCase):
    def test_gb_render_keeps_structured_fields_and_number(self):
        ref = {
            "author_list": ["Smith J", "Lee K"],
            "title": "Deep learning study",
            "source": "Nature",
            "year": "2024",
            "volume": "35",
            "issue": "2",
            "pages": "12-20",
            "doi": "10.1038/test1234",
        }
        rendered = render_reference(ref, 1, "gb7714", {"citation_style": "superscript"})
        self.assertEqual(
            rendered,
            "[1] Smith J, Lee K. Deep learning study. Nature, 35(2): 12-20, 2024. DOI:10.1038/test1234.",
        )

    def test_journal_rules_do_not_replace_gb_citation_grammar(self):
        refs = [{"author_list": ["Wang L"], "authors": "Wang L", "title": "A method study", "source": "Science", "year": "2023", "volume": "12", "issue": "1", "pages": "30-40"}]
        result = render_references(refs, "gb7714", {"citation_style": "superscript", "pages_prefix": "pp."})
        self.assertTrue(result[0]["formatted"].startswith("[1] Wang L."))
        self.assertNotIn("Vol.", result[0]["formatted"])
        self.assertNotIn("No.", result[0]["formatted"])


if __name__ == "__main__":
    unittest.main()
