import tempfile
import unittest
from pathlib import Path

from src.capa1_ingesta import collect_input_files


class TestCapa1Ingesta(unittest.TestCase):
    def test_collect_input_files_with_exclusion(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            (base / "a.pdf").write_text("x", encoding="utf-8")
            (base / "b.docx").write_text("x", encoding="utf-8")
            (base / "c.txt").write_text("x", encoding="utf-8")

            files = collect_input_files(base, {"B.DOCX"})
            self.assertEqual([f.name for f in files], ["a.pdf"])


if __name__ == "__main__":
    unittest.main()
