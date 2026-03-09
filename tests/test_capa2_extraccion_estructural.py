import unittest

from src.capa2_extraccion_estructural import (
    detect_referenciables,
    normalize_text,
    pages_to_markdown,
)


class TestCapa2Extraccion(unittest.TestCase):
    def test_normalize_text(self):
        txt = "Linea 1\r\nLinea 2  \rLinea 3\n"
        self.assertEqual(normalize_text(txt), "Linea 1\nLinea 2\nLinea 3")

    def test_detect_referenciables(self):
        page = (
            "Como se observa en Tabla 2-14, el impacto es moderado. "
            "Ver Figura 3.2 y Numeral 4.1.3 para mayor detalle."
        )
        refs = detect_referenciables(page, 10, "cap7.pdf")
        tipos = sorted([r.tipo for r in refs])
        ids = sorted([r.id_detectado.lower() for r in refs])
        self.assertEqual(tipos, ["figura", "numeral", "tabla"])
        self.assertIn("tabla 2-14", ids)
        self.assertIn("figura 3.2", ids)
        self.assertIn("numeral 4.1.3", ids)

    def test_pages_to_markdown(self):
        pages = ["1.1 Introducción\nTexto base", ""]
        md = pages_to_markdown(pages, "cap1.pdf")
        self.assertIn("# Documento: cap1.pdf", md)
        self.assertIn("## Página 1", md)
        self.assertIn("### 1.1 Introducción", md)
        self.assertIn("_Página sin texto extraíble._", md)


if __name__ == "__main__":
    unittest.main()
