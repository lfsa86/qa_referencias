import unittest

from src.capa2_extraccion_estructural import (
    detect_referenciables,
    format_heading_line,
    is_likely_toc_page,
    normalize_text,
    pages_to_markdown,
    remove_toc_noise,
)


class TestCapa2Extraccion(unittest.TestCase):
    def test_normalize_text(self):
        txt = "Linea 1\r\nLinea 2  \rLinea 3\n"
        self.assertEqual(normalize_text(txt), "Linea 1\nLinea 2\nLinea 3")

    def test_detect_referenciables(self):
        page = (
            "Tabla 2-14 ........ 45\n"
            "Figura 3.2 ....... 46\n"
            "Numeral 4.1.3 .... 47"
        )
        refs = detect_referenciables(page, 10, "cap7.pdf")
        tipos = sorted([r.tipo for r in refs])
        ids = sorted([r.id_detectado.lower() for r in refs])
        self.assertEqual(tipos, ["figura", "numeral", "tabla"])
        self.assertIn("tabla 2-14", ids)
        self.assertIn("figura 3.2", ids)
        self.assertIn("numeral 4.1.3", ids)


    def test_detect_referenciables_identificador_compuesto_tabla(self):
        page = "Tabla 3.3.6-1 ........ 7"
        refs = detect_referenciables(page, 2, "cap3.pdf")
        self.assertEqual(len(refs), 1)
        self.assertEqual(refs[0].tipo, "tabla")
        self.assertEqual(refs[0].id_detectado.lower(), "tabla 3.3.6-1")

    def test_pages_to_markdown(self):
        pages = ["1.1 Introducción\nTexto base", ""]
        md = pages_to_markdown(pages, "cap1.pdf")
        self.assertIn("# Documento: cap1.pdf", md)
        self.assertIn("## Página 1", md)
        self.assertIn("### 1.1 Introducción", md)
        self.assertIn("_Página sin texto extraíble._", md)

    def test_format_heading_line_numero_pegado_a_titulo(self):
        line = "5.2.4.1.7.2Hidrología: Impacto RH-2"
        formatted = format_heading_line(line)
        self.assertEqual(formatted, "###### 5.2.4.1.7.2 Hidrología: Impacto RH-2")

    def test_remove_toc_noise_descarta_entradas_toc(self):
        lines = [
            "Tabla de contenidos",
            "5.2.4.1.7.2Hidrología: Impacto RH-2 Cambio del régimen hidrológico y caudal5.2.4.1.7-106",
            "5.2.4.1.7.2.1Metodología para el análisis de impacto5.2.4.1.7-106",
            "Texto cuerpo real",
        ]
        cleaned = remove_toc_noise(lines)
        self.assertEqual(cleaned, ["Tabla de contenidos", "Texto cuerpo real"])
        self.assertTrue(is_likely_toc_page(lines))

    def test_detect_referenciables_solo_tabla_contenido(self):
        page = "Texto narrativo con Tabla 2-14 y Figura 3.2, sin puntos guía ni paginación"
        refs = detect_referenciables(page, 1, "cap7.pdf")
        self.assertEqual(refs, [])

    def test_detect_referenciables_linea_toc_markdown_con_numero_pagina_compuesto(self):
        page = "### 3.3.6.1.1 Intervención humana a través de actividades productivas 3.3.6-2"
        refs = detect_referenciables(page, 2, "cap3.pdf")
        self.assertEqual(len(refs), 1)
        self.assertEqual(refs[0].tipo, "numeral")
        self.assertEqual(refs[0].id_detectado, "3.3.6.1.1")

    def test_detect_referenciables_linea_toc_markdown_tabla_con_pagina_compuesta(self):
        page = "Tabla 3.3.6-2: Amenazas identificadas para hábitats 3.3.6-2"
        refs = detect_referenciables(page, 2, "cap3.pdf")
        self.assertEqual(len(refs), 1)
        self.assertEqual(refs[0].tipo, "tabla")
        self.assertEqual(refs[0].id_detectado.lower(), "tabla 3.3.6-2")


    def test_detect_referenciables_grafico_en_toc(self):
        page = "Gráfico 3.4 ....... 12\nGrafico 2-1 ........ 5"
        refs = detect_referenciables(page, 3, "cap3.pdf")
        tipos_ids = sorted((r.tipo, r.id_detectado.lower()) for r in refs)
        self.assertEqual(
            tipos_ids,
            [("figura", "grafico 2-1"), ("figura", "gráfico 3.4")],
        )


if __name__ == "__main__":
    unittest.main()
