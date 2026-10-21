import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from app.storage import Store
from app.template_search import cache_candidate, search_templates


class SchoolTemplateCacheTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.temp_dir.name) / "templates.sqlite3")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_candidate_is_cached_with_scope_and_pending_review_status(self):
        item = cache_candidate(self.store, {
            "degree": "graduate",
            "school": "示例大学",
            "college": "计算机学院",
            "title": "研究生学位论文规范",
            "url": "https://grad.example.edu.cn/thesis",
            "snippet": "规范文件",
        })

        cached = search_templates(self.store, "graduate", "示例大学", "计算机学院")
        self.assertTrue(cached["cached"])
        self.assertEqual(cached["results"][0]["id"], item["id"])
        self.assertEqual(cached["results"][0]["status"], "candidate")

    def test_cache_candidate_rejects_non_http_source(self):
        with self.assertRaises(ValueError):
            cache_candidate(self.store, {
                "degree": "undergraduate",
                "school": "示例大学",
                "title": "模板",
                "url": "javascript:alert(1)",
            })

    def test_cache_miss_explains_search_configuration(self):
        with patch("app.template_search.settings", SimpleNamespace(template_search_api_key="")):
            result = search_templates(self.store, "undergraduate", "示例大学")
        self.assertFalse(result["cached"])
        self.assertFalse(result["configured"])
        self.assertIn("TAVILY_API_KEY", result["message"])


if __name__ == "__main__":
    unittest.main()
