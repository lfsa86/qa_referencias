import unittest

from src.capa4_extraccion_referencias_cap7 import (
    extract_references,
    split_markdown_pages,
)


class TestCapa4ExtraccionReferenciasCap7(unittest.TestCase):
    def test_split_markdown_pages(self):
        txt = "# Documento\n\n## Página 1\nA\n\n## Página 2\nB"
        pages = split_markdown_pages(txt)
        self.assertEqual(len(pages), 2)
        self.assertEqual(pages[0], "A")
        self.assertEqual(pages[1], "B")

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
