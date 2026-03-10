import tempfile
import unittest
import zipfile
from pathlib import Path

from src.capa4_extraccion_referencias_cap7 import (
    extract_references,
    load_text,
    split_markdown_pages,
)


class TestCapa4ExtraccionReferenciasCap7(unittest.TestCase):
    def test_split_markdown_pages(self):
        txt = "# Documento\n\n## Página 1\nA\n\n## Página 2\nB"
        pages = split_markdown_pages(txt)
        self.assertEqual(len(pages), 2)
        self.assertEqual(pages[0], "A")
        self.assertEqual(pages[1], "B")


    def test_load_text_from_docx(self):
        with tempfile.TemporaryDirectory() as td:
            docx_path = Path(td) / "cap7.docx"
            with zipfile.ZipFile(docx_path, "w") as zf:
                zf.writestr(
                    "word/document.xml",
                    """<?xml version="1.0" encoding="UTF-8"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p><w:r><w:t>Tabla 2-14</w:t></w:r></w:p>
    <w:p><w:r><w:t>Numeral 4.1.3</w:t></w:r></w:p>
  </w:body>
</w:document>
""",
                )

            text = load_text(docx_path)
            self.assertIn("Tabla 2-14", text)
            self.assertIn("Numeral 4.1.3", text)

    def test_extract_references(self):
        md = """
# Documento: cap7.pdf

## Página 1
Según la Tabla 2-14 y Figura 3.2, los impactos son moderados.

Además, revisar Numeral 4.1.3 y 5.2.1 para completar análisis.

## Página 2
Sin referencias.
"""
        refs = extract_references(md, "cap7.md")
        tipos_ids = {(r.tipo, r.id_normalizado, r.capitulo_objetivo) for r in refs}

        self.assertIn(("tabla", "Tabla 2-14", "cap2"), tipos_ids)
        self.assertIn(("figura", "Figura 3-2", "cap3"), tipos_ids)
        self.assertIn(("numeral", "4-1-3", "cap4"), tipos_ids)
        self.assertIn(("numeral", "5-2-1", "cap5"), tipos_ids)


if __name__ == "__main__":
    unittest.main()
