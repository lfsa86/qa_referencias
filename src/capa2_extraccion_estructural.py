#!/usr/bin/env python3
"""Capa 2 - Extracción estructural (PDF -> Markdown).

Submódulos incluidos:
- 2.1 Extracción de texto y bloques (texto por página).
- 2.2 Detección de elementos referenciables (tabla/figura/numeral).

Requiere `pypdf` para leer PDFs.
"""

from __future__ import annotations

import argparse
import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


CSV_ENCODING = "utf-8-sig"

TABLA_REGEX = re.compile(r"\b(Tabla\s+\d+[.-]\d+)\b", re.IGNORECASE)
FIGURA_REGEX = re.compile(r"\b(Figura\s+\d+[.-]\d+)\b", re.IGNORECASE)
NUMERAL_REGEX = re.compile(r"\b((?:Numeral\s+\d+(?:\.\d+)+)|(?:\d+\.\d+\.\d+))\b", re.IGNORECASE)
HEADING_REGEX = re.compile(r"^\s*(\d+(?:\.\d+)+)\s+(.+)$")


@dataclass
class Referenciable:
    archivo: str
    pagina: int
    tipo: str
    id_detectado: str
    titulo_o_contexto: str
    snippet: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Capa 2: PDF -> Markdown + elementos referenciables")
    parser.add_argument("--input-dir", type=Path, required=True, help="Directorio con PDFs de entrada")
    parser.add_argument("--output-dir", type=Path, default=Path("out/capa2"), help="Directorio de salida")
    return parser.parse_args()


def extract_text_pages(pdf_path: Path) -> list[str]:
    try:
        from pypdf import PdfReader  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "Dependencia faltante: instala `pypdf` (pip install pypdf) para ejecutar la Capa 2."
        ) from exc

    reader = PdfReader(str(pdf_path))
    pages: list[str] = []
    for page in reader.pages:
        text = page.extract_text() or ""
        pages.append(normalize_text(text))
    return pages


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [ln.rstrip() for ln in text.split("\n")]
    return "\n".join(lines).strip()


def pages_to_markdown(pages: Iterable[str], source_name: str) -> str:
    chunks = [f"# Documento: {source_name}"]
    for i, page_text in enumerate(pages, start=1):
        chunks.append(f"\n## Página {i}\n")
        if not page_text.strip():
            chunks.append("_Página sin texto extraíble._")
            continue
        for line in page_text.split("\n"):
            m = HEADING_REGEX.match(line)
            if m:
                chunks.append(f"### {m.group(1)} {m.group(2).strip()}")
            else:
                chunks.append(line)
    return "\n".join(chunks).strip() + "\n"


def detect_referenciables(page_text: str, page_number: int, source_name: str) -> list[Referenciable]:
    results: list[Referenciable] = []

    def add_matches(pattern: re.Pattern[str], tipo: str) -> None:
        for match in pattern.finditer(page_text):
            snippet = page_text[max(0, match.start() - 80) : min(len(page_text), match.end() + 80)]
            results.append(
                Referenciable(
                    archivo=source_name,
                    pagina=page_number,
                    tipo=tipo,
                    id_detectado=match.group(1),
                    titulo_o_contexto=context_from_snippet(snippet),
                    snippet=snippet.replace("\n", " ").strip(),
                )
            )

    add_matches(TABLA_REGEX, "tabla")
    add_matches(FIGURA_REGEX, "figura")
    add_matches(NUMERAL_REGEX, "numeral")
    return results


def context_from_snippet(snippet: str) -> str:
    clean = " ".join(snippet.replace("\n", " ").split())
    if len(clean) <= 120:
        return clean
    return clean[:117] + "..."


def write_markdown(md_path: Path, content: str) -> None:
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(content, encoding="utf-8")


def write_elements_csv(csv_path: Path, rows: list[Referenciable]) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="", encoding=CSV_ENCODING) as f:
        writer = csv.writer(f)
        writer.writerow(["archivo", "pagina", "tipo", "id_detectado", "titulo_o_contexto", "snippet"])
        for r in rows:
            writer.writerow([r.archivo, r.pagina, r.tipo, r.id_detectado, r.titulo_o_contexto, r.snippet])


def process_pdf(pdf_path: Path, output_dir: Path) -> tuple[Path, Path, int]:
    pages = extract_text_pages(pdf_path)
    markdown = pages_to_markdown(pages, pdf_path.name)

    elementos: list[Referenciable] = []
    for i, page_text in enumerate(pages, start=1):
        elementos.extend(detect_referenciables(page_text, i, pdf_path.name))

    md_path = output_dir / "markdown" / f"{pdf_path.stem}.md"
    csv_path = output_dir / "elementos" / f"{pdf_path.stem}_elementos.csv"
    write_markdown(md_path, markdown)
    write_elements_csv(csv_path, elementos)
    return md_path, csv_path, len(elementos)


def main() -> int:
    args = parse_args()
    input_dir = args.input_dir.resolve()
    output_dir = args.output_dir.resolve()

    if not input_dir.exists() or not input_dir.is_dir():
        print(f"ERROR: input-dir inválido: {input_dir}")
        return 2

    pdfs = sorted([p for p in input_dir.iterdir() if p.is_file() and p.suffix.lower() == ".pdf"])
    if not pdfs:
        print(f"ERROR: no se encontraron PDFs en {input_dir}")
        return 2

    total_elements = 0
    for pdf in pdfs:
        md, csv_path, count = process_pdf(pdf, output_dir)
        total_elements += count
        print(f"OK: {pdf.name} -> {md} | {csv_path} | elementos={count}")

    print(f"Resumen: pdfs={len(pdfs)} elementos={total_elements} output={output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
