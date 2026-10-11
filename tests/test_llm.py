import json
import unittest
from unittest.mock import patch

from app import llm


class LlmReferenceNormalizationTests(unittest.TestCase):
    @patch("app.llm.settings")
    @patch("app.llm.urllib.request.urlopen")
    def test_normalize_references_returns_metadata_only(self, urlopen, settings):
        settings.llm_api_key = "test-key"
        settings.llm_api_url = "https://api.deepseek.com/chat/completions"
        settings.llm_model = "deepseek-flash"
        response = {
            "choices": [{"message": {"content": json.dumps([
                {
                    "index": 1,
                    "authors": "Smith J, Lee K",
                    "title": "Deep learning study",
                    "source": "Nature",
                    "year": "2024",
                    "volume": "35",
                    "issue": "2",
                    "pages": "12-20",
                    "doi": "10.1038/test1234",
                    "url": "",
                    "reference_type": "journal",
                }
            ])}}],
        }

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self):
                return json.dumps(response).encode("utf-8")

        urlopen.return_value = FakeResponse()
        result = llm.normalize_references(
            [{"index": 1, "raw": "Smith J, Lee K. Deep learning study."}], "gb7714"
        )

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["references"][0]["doi"], "10.1038/test1234")
        request = urlopen.call_args.args[0]
        sent = json.loads(request.data.decode("utf-8"))
        self.assertEqual(sent["model"], "deepseek-flash")
        self.assertIn("Deep learning study", sent["messages"][1]["content"])
        self.assertNotIn("这是正文内容", sent["messages"][1]["content"])

    @patch("app.llm.configured", return_value=False)
    def test_normalize_skips_when_not_configured(self, _configured):
        self.assertIsNone(llm.normalize_references([{"index": 1}], "gb7714"))


if __name__ == "__main__":
    unittest.main()
