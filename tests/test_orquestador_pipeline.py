import unittest
from unittest.mock import patch

from src.orquestador_pipeline import select_ocr_engine


class TestOrquestadorPipeline(unittest.TestCase):
    def test_select_ocr_engine_respects_explicit_value(self):
        self.assertEqual(select_ocr_engine("pypdf"), "pypdf")
        self.assertEqual(select_ocr_engine("mistral"), "mistral")

    @patch("builtins.input", side_effect=["2"])
    def test_select_ocr_engine_interactive_numeric_choice(self, _mock_input):
        self.assertEqual(select_ocr_engine(None), "mistral")

    @patch("builtins.input", side_effect=["foo", "pypdf"])
    def test_select_ocr_engine_retries_until_valid(self, _mock_input):
        self.assertEqual(select_ocr_engine(None), "pypdf")


if __name__ == "__main__":
    unittest.main()
