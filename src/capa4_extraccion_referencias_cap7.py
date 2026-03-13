#!/usr/bin/env python3
"""Capa 4 - Extracción de referencias desde capítulo 7.

Lee markdown (preferente) o texto plano de cap7 y detecta referencias cruzadas
hacia capítulos previos (tabla, figura, numeral).
"""

from __future__ import annotations

import argparse
import csv
import re
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass
from pathlib import Path

CSV_ENCODING = "utf-8-sig"

TABLA_REGEX = re.compile(r"\b(Tabla\s+([1-7])[.-](\d+))\b", re.IGNORECASE)
FIGURA_REGEX = re.compile(r"\b(Figura\s+([1-7])[.-](\d+))\b", re.IGNORECASE)
NUMERAL_FULL_REGEX = re.compile(r"\b(Numeral\s+([1-7])((?:\.\d+)+))\b", re.IGNORECASE)
NUMERAL_SHORT_REGEX = re.compile(r"\b([1-6](?:\.\d+){2,})\b")


@dataclass
class RefCap7:
    archivo: str
    pagina: int
    parrafo_idx: int
    tipo: str
    referencia_original: str
    capitulo_objetivo: str
    id_normalizado: str
    contexto: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Capa 4: extracción de referencias desde capítulo 7")
    parser.add_argument("--cap7-file", type=Path, required=True, help="Archivo cap7 en .md, .txt o .docx")
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=Path("out/referencias_cap7.csv"),
        help="Ruta salida CSV con referencias detectadas.",
    )
    return parser.parse_args()


def load_text(path: Path) -> str:
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"Archivo no encontrado: {path}")

    if path.suffix.lower() == ".docx":
        return load_docx_text(path)

    return path.read_text(encoding="utf-8", errors="ignore")


def load_docx_text(path: Path) -> str:
    """Extrae texto de un .docx usando XML interno sin dependencias externas."""
    try:
        with zipfile.ZipFile(path) as zf:
            xml_bytes = zf.read("word/document.xml")
    except (KeyError, zipfile.BadZipFile, FileNotFoundError) as exc:
        raise RuntimeError(f"No se pudo leer DOCX: {path}") from exc

    root = ET.fromstring(xml_bytes)
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}

    paragraphs: list[str] = []
    for p in root.findall(".//w:p", ns):
        runs = [node.text for node in p.findall(".//w:t", ns) if node.text]
        text = "".join(runs).strip()
        if text:
            paragraphs.append(text)

    return "\n\n".join(paragraphs)


def split_markdown_pages(md_text: str) -> list[str]:
    # Espera formato de Capa 2: '## Página N'
    blocks = re.split(r"(?m)^##\s+Página\s+\d+\s*$", md_text)
    if len(blocks) <= 1:
        return [md_text]
    # El primer bloque puede contener cabecera del documento
    pages = [b.strip() for b in blocks[1:]]
    return pages


def normalize_table_figure(tipo: str, chapter_num: str, item_num: str) -> str:
    prefix = "Tabla" if tipo == "tabla" else "Figura"
    return f"{prefix} {chapter_num}-{item_num}"


def normalize_numeral(chapter_num: str, suffix: str) -> str:
    return f"{chapter_num}{suffix.replace('.', '-')}"


def context_window(text: str, start: int, end: int, size: int = 90) -> str:
    snippet = text[max(0, start - size) : min(len(text), end + size)]
    return " ".join(snippet.split())


def detect_refs_in_paragraph(paragraph: str, page_num: int, parrafo_idx: int, source_name: str) -> list[RefCap7]:
    refs: list[RefCap7] = []

    for m in TABLA_REGEX.finditer(paragraph):
        chapter_num = m.group(2)
        refs.append(
            RefCap7(
                archivo=source_name,
                pagina=page_num,
                parrafo_idx=parrafo_idx,
                tipo="tabla",
                referencia_original=m.group(1),
                capitulo_objetivo=f"cap{chapter_num}",
                id_normalizado=normalize_table_figure("tabla", chapter_num, m.group(3)),
                contexto=context_window(paragraph, m.start(), m.end()),
            )
        )

    for m in FIGURA_REGEX.finditer(paragraph):
        chapter_num = m.group(2)
        refs.append(
            RefCap7(
                archivo=source_name,
                pagina=page_num,
                parrafo_idx=parrafo_idx,
                tipo="figura",
                referencia_original=m.group(1),
                capitulo_objetivo=f"cap{chapter_num}",
                id_normalizado=normalize_table_figure("figura", chapter_num, m.group(3)),
                contexto=context_window(paragraph, m.start(), m.end()),
            )
        )

    for m in NUMERAL_FULL_REGEX.finditer(paragraph):
        chapter_num = m.group(2)
        refs.append(
            RefCap7(
                archivo=source_name,
                pagina=page_num,
                parrafo_idx=parrafo_idx,
                tipo="numeral",
                referencia_original=m.group(1),
                capitulo_objetivo=f"cap{chapter_num}",
                id_normalizado=normalize_numeral(chapter_num, m.group(3)),
                contexto=context_window(paragraph, m.start(), m.end()),
            )
        )

    # Numerales sin palabra 'Numeral', evitando duplicar matches ya capturados.
    for m in NUMERAL_SHORT_REGEX.finditer(paragraph):
        if "numeral" in paragraph[max(0, m.start() - 10) : m.start()].lower():
            continue
        raw = m.group(1)
        chapter_num = raw.split(".")[0]
        suffix = raw[len(chapter_num) :]
        refs.append(
            RefCap7(
                archivo=source_name,
                pagina=page_num,
                parrafo_idx=parrafo_idx,
                tipo="numeral",
                referencia_original=raw,
                capitulo_objetivo=f"cap{chapter_num}",
                id_normalizado=normalize_numeral(chapter_num, suffix),
                contexto=context_window(paragraph, m.start(), m.end()),
            )
        )

    return refs


def deduplicate(refs: list[RefCap7]) -> list[RefCap7]:
    seen: set[tuple[int, int, str, str]] = set()
    out: list[RefCap7] = []
    for r in refs:
        key = (r.pagina, r.parrafo_idx, r.tipo, r.id_normalizado)
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
    return out


def extract_references(md_or_txt: str, source_name: str) -> list[RefCap7]:
    pages = split_markdown_pages(md_or_txt)
    all_refs: list[RefCap7] = []

    for page_i, page_text in enumerate(pages, start=1):
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", page_text) if p.strip()]
        for parrafo_idx, paragraph in enumerate(paragraphs, start=1):
            all_refs.extend(detect_refs_in_paragraph(paragraph, page_i, parrafo_idx, source_name))

    return deduplicate(all_refs)


def write_csv(path: Path, refs: list[RefCap7]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding=CSV_ENCODING, newline="") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "archivo",
                "pagina",
                "parrafo_idx",
                "tipo",
                "referencia_original",
                "capitulo_objetivo",
                "id_normalizado",
                "contexto",
            ]
        )
        for r in refs:
            w.writerow(
                [
                    r.archivo,
                    r.pagina,
                    r.parrafo_idx,
                    r.tipo,
                    r.referencia_original,
                    r.capitulo_objetivo,
                    r.id_normalizado,
                    r.contexto,
                ]
            )


def main() -> int:
    args = parse_args()
    cap7_path = args.cap7_file.resolve()
    output_csv = args.output_csv.resolve()

    try:
        text = load_text(cap7_path)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}")
        return 2

    refs = extract_references(text, cap7_path.name)
    write_csv(output_csv, refs)

    print(f"Referencias detectadas: {len(refs)}")
    print(f"Salida: {output_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
