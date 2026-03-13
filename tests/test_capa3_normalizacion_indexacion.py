import csv
import tempfile
import unittest
from pathlib import Path

from src.capa3_normalizacion_indexacion import (
    chapter_from_reference,
    deduplicate,
    load_element_rows,
    normalize_id,
    normalize_type,
)


class TestCapa3NormalizacionIndexacion(unittest.TestCase):
    def test_normalize_type(self):
        self.assertEqual(normalize_type("ítem"), "item")
        self.assertEqual(normalize_type("sección"), "seccion")
        self.assertEqual(normalize_type("tabla"), "tabla")

    def test_normalize_id(self):
        self.assertEqual(normalize_id("tabla", "tabla 2.14"), "Tabla 2-14")
        self.assertEqual(normalize_id("figura", "FIGURA 3.2"), "Figura 3-2")
        self.assertEqual(normalize_id("numeral", "Numeral 4.1.3"), "4-1-3")


    def test_chapter_from_reference(self):
        self.assertEqual(chapter_from_reference("Tabla 3.3.6-1"), "cap3")
        self.assertEqual(chapter_from_reference("Numeral 6.2.1"), "cap6")
        self.assertEqual(chapter_from_reference("sin patrón"), "desconocido")

    def test_load_and_deduplicate(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "cap2_elementos.csv"
            with p.open("w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["archivo", "pagina", "tipo", "id_detectado", "titulo_o_contexto", "snippet"])
                w.writerow(["cap2.pdf", 10, "tabla", "Tabla 2-14", "Calidad de agua", "..."])
                w.writerow(["cap2.pdf", 10, "tabla", "Tabla 2-14", "Calidad de agua", "..."])
                w.writerow(["folio_3.3.6.pdf", 2, "tabla", "Tabla 3.3.6-1", "Unidades", "..."])

            rows = load_element_rows(p, "v12")
            self.assertEqual(len(rows), 3)
            dedup = deduplicate(rows)
            self.assertEqual(len(dedup), 2)
            self.assertEqual(dedup[0].capitulo, "cap2")
            self.assertEqual(dedup[0].version, "v12")
            self.assertEqual(dedup[1].capitulo, "cap3")


if __name__ == "__main__":
    unittest.main()
