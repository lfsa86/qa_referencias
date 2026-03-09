import unittest

from src.capa6_reporte_control_calidad import (
    ValidationResult,
    build_renumeraciones,
    build_resumen,
)


class TestCapa6ReporteControlCalidad(unittest.TestCase):
    def test_build_resumen(self):
        rows = [
            ValidationResult("cap7.md", 1, 1, "tabla", "Tabla 2-14", "cap2", "Tabla 2-14", "OK", "", "", "", 0, 1.0),
            ValidationResult("cap7.md", 1, 2, "tabla", "Tabla 2-99", "cap2", "Tabla 2-99", "REVISAR_RENUMERACION", "", "Tabla 2-14", "", 10, 0.9),
            ValidationResult("cap7.md", 2, 1, "figura", "Figura 3-1", "cap3", "Figura 3-1", "ERROR_NO_EXISTE", "", "", "", 0, 0.0),
        ]
        resumen = build_resumen(rows)
        self.assertIn(("estado", "OK", 1), resumen)
        self.assertIn(("estado", "REVISAR_RENUMERACION", 1), resumen)
        self.assertIn(("capitulo_objetivo", "cap2", 2), resumen)

    def test_build_renumeraciones(self):
        rows = [
            ValidationResult("cap7.md", 1, 1, "tabla", "Tabla 2-99", "cap2", "Tabla 2-99", "REVISAR_RENUMERACION", "", "Tabla 2-14", "", 10, 0.9),
            ValidationResult("cap7.md", 1, 2, "tabla", "Tabla 2-14", "cap2", "Tabla 2-14", "OK", "", "", "", 0, 1.0),
        ]
        ren = build_renumeraciones(rows)
        self.assertEqual(len(ren), 1)
        self.assertEqual(ren[0].id_match, "Tabla 2-14")


if __name__ == "__main__":
    unittest.main()
