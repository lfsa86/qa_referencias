import csv
import tempfile
import unittest
import zipfile
from pathlib import Path

from src.capa4_extraccion_referencias_cap7 import (
    excel_safe_text,
    extract_references,
    infer_page_from_context,
    load_text,
    split_markdown_pages,
    to_feedback_markdown,
    write_csv,
)


class TestCapa4ExtraccionReferenciasCap7(unittest.TestCase):
    def test_split_markdown_pages(self):
        txt = "# Documento\n\n## Página 1\nA\n\n## Página 2\nB"
        pages = split_markdown_pages(txt)
        self.assertEqual(len(pages), 2)
        self.assertEqual(pages[0], "A")
        self.assertEqual(pages[1], "B")

    def test_load_text_docx(self):
        with tempfile.TemporaryDirectory() as td:
            docx = Path(td) / "cap7.docx"
            with zipfile.ZipFile(docx, "w") as zf:
                zf.writestr(
                    "word/document.xml",
                    """
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p><w:r><w:t>Ver Tabla 2-14.</w:t></w:r></w:p>
    <w:p><w:r><w:t>Revisar Numeral 4.1.3.</w:t></w:r></w:p>
  </w:body>
</w:document>
""",
                )

            text = load_text(docx)
            self.assertIn("Ver Tabla 2-14.", text)
            self.assertIn("Revisar Numeral 4.1.3.", text)

    def test_to_feedback_markdown(self):
        text = "Linea 1\n\nLinea 2"
        md = to_feedback_markdown(text, "cap7.docx")

        self.assertIn("# Documento: cap7.docx", md)
        self.assertIn("## Página 1", md)
        self.assertIn("Linea 1", md)
        self.assertIn("Linea 2", md)

    def test_infer_page_from_context(self):
        self.assertEqual(infer_page_from_context("Tabla 7.2.41:Parámetros ... 7.2-20\"", 1), 20)
        self.assertEqual(infer_page_from_context("sin patrón", 3), 3)

    def test_extract_references_usa_pagina_en_contexto(self):
        text = "Según Tabla 2.4 para detalle 7.2-20\""
        refs = extract_references(text, "cap7.txt")
        self.assertEqual(len(refs), 1)
        self.assertEqual(refs[0].pagina, 20)

    def test_extract_references(self):
        md = """
# Documento: cap7.pdf

## Página 1
Según la Tabla 2-14, Figura 3.2 y Gráfico 6-4, los impactos son moderados.

Además, revisar Numeral 4.1.3 y 5.2.1 para completar análisis.

## Página 2
Sin referencias.
"""
        refs = extract_references(md, "cap7.md")
        tipos_ids = {(r.tipo, r.id_normalizado, r.capitulo_objetivo) for r in refs}

        self.assertIn(("tabla", "Tabla 2-14", "cap2"), tipos_ids)
        self.assertIn(("figura", "Figura 3-2", "cap3"), tipos_ids)
        self.assertIn(("figura", "Figura 6-4", "cap6"), tipos_ids)
        self.assertIn(("numeral", "4-1-3", "cap4"), tipos_ids)
        self.assertIn(("numeral", "5-2-1", "cap5"), tipos_ids)
        self.assertTrue(all(r.confianza in {"alta", "media", "baja"} for r in refs))

    def test_extract_references_detecta_referencias_especiales(self):
        text = (
            "Figura PIC 5.2.4.1.7.2-1: Manejo de aguas.\n"
            "Tabla LO 5.2.4.1.7.2-2: Caudales medios.\n"
            "Anexo PIC 5.2.4.1.7.4: Resultados de simulaciones."
        )
        refs = extract_references(text, "cap7.txt")
        tipos_ids = {(r.tipo, r.id_normalizado, r.capitulo_objetivo) for r in refs}

        self.assertIn(("figura", "Figura PIC 5-2-4-1-7-2-1", "cap5"), tipos_ids)
        self.assertIn(("tabla", "Tabla LO 5-2-4-1-7-2-2", "cap5"), tipos_ids)
        self.assertIn(("anexo", "Anexo PIC 5-2-4-1-7-4", "cap5"), tipos_ids)

    def test_extract_references_ignora_numerales_ruidosos(self):
        text = "Ruido 2.2.20515151515151 y referencia válida 4.3.2 en el mismo párrafo."
        refs = extract_references(text, "cap7.txt")
        ids = {(r.referencia_original, r.id_normalizado) for r in refs}

        self.assertIn(("4.3.2", "4-3-2"), ids)
        self.assertNotIn(("2.2.20515151515151", "2-2-20515151515151"), ids)

    def test_no_toma_submatches_en_numerales_largos_de_cap7(self):
        text = "7.2.4.1.1Servicio de aprovisionamiento: Pastizales para pastoreo de ganado7.2-20"
        refs = extract_references(text, "cap7.txt")
        self.assertEqual(refs, [])

    def test_tabla_larga_no_trunca_en_prefijo(self):
        text = "Según la Tabla 5.2.4.1.5-7, se identifican coberturas."
        refs = extract_references(text, "cap7.txt")
        self.assertEqual(len(refs), 1)
        self.assertEqual(refs[0].tipo, "tabla")
        self.assertEqual(refs[0].id_normalizado, "Tabla 5-2-4-1-5-7")

    def test_excel_safe_export_columns(self):
        text = "Revisar 4.1.3 y Tabla 2-14."
        refs = extract_references(text, "cap7.txt")

        with tempfile.TemporaryDirectory() as td:
            csv_path = Path(td) / "refs.csv"
            write_csv(csv_path, refs)

            with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
                rows = list(csv.DictReader(f))

        self.assertGreaterEqual(len(rows), 1)
        self.assertIn("id_normalizado_excel_safe", rows[0])
        self.assertIn("referencia_original_excel_safe", rows[0])
        self.assertTrue(rows[0]["id_normalizado_excel_safe"].startswith('="'))

    def test_excel_safe_text(self):
        self.assertEqual(excel_safe_text("4-1-3"), '="4-1-3"')


if __name__ == "__main__":
    unittest.main()
