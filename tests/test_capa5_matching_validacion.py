import unittest

from src.capa5_matching_validacion import (
    IndexEntry,
    RefEntry,
    validate_all,
    validate_one,
)


class TestCapa5MatchingValidacion(unittest.TestCase):
    def setUp(self):
        self.index_rows = [
            IndexEntry("cap2", "tabla", "Tabla 2-14", "Tabla 2-14", "Calidad de agua superficial", 10, "h1", "v1", "cap2.pdf"),
            IndexEntry("cap3", "figura", "Figura 3-2", "Figura 3-2", "Mapa de cobertura vegetal", 20, "h2", "v1", "cap3.pdf"),
            IndexEntry("cap4", "numeral", "4-1-3", "Numeral 4.1.3", "Metodología de evaluación", 30, "h3", "v1", "cap4.pdf"),
            IndexEntry("cap2", "tabla", "Tabla 2-15", "Tabla 2-15", "Calidad del agua subterránea", 11, "h4", "v1", "cap2.pdf"),
        ]

    def test_ok_exact_match(self):
        ref = RefEntry("cap7.md", 1, 1, "tabla", "Tabla 2-14", "cap2", "Tabla 2-14", "Calidad de agua superficial")
        row = validate_one(ref, self.index_rows, threshold=0.7)
        self.assertEqual(row.estado, "OK")

    def test_error_no_existe(self):
        ref = RefEntry("cap7.md", 1, 1, "figura", "Figura 6-9", "cap6", "Figura 6-9", "sin contexto")
        row = validate_one(ref, self.index_rows, threshold=0.9)
        self.assertEqual(row.estado, "ERROR_NO_EXISTE")

    def test_revisar_renumeracion(self):
        ref = RefEntry(
            "cap7.md",
            2,
            1,
            "tabla",
            "Tabla 2-99",
            "cap2",
            "Tabla 2-99",
            "Calidad del agua subterránea",
        )
        row = validate_one(ref, self.index_rows, threshold=0.7)
        self.assertEqual(row.estado, "REVISAR_RENUMERACION")
        self.assertEqual(row.id_match, "Tabla 2-15")



    def test_validate_all_excluye_referencias_cap7(self):
        refs = [
            RefEntry("cap7.md", 1, 1, "tabla", "Tabla 2-14", "cap2", "Tabla 2-14", "Calidad de agua superficial"),
            RefEntry("cap7.md", 1, 2, "tabla", "Tabla 7-1", "cap7", "Tabla 7-1", "interna cap7"),
        ]

        rows = validate_all(refs, self.index_rows, threshold=0.7)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].capitulo_objetivo, "cap2")

if __name__ == "__main__":
    unittest.main()
