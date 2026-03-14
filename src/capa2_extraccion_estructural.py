#!/usr/bin/env python3
"""Capa 2 - Extracción estructural (PDF/DOCX -> Markdown).

Submódulos incluidos:
- 2.1 Extracción de texto y bloques (texto por página).
- 2.2 Detección de elementos referenciables desde la tabla de contenido.

Requiere `pypdf` para leer PDFs.
"""

from __future__ import annotations

import argparse
import csv
import os
import re
import time
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from xml.etree import ElementTree as ET


CSV_ENCODING = "utf-8-sig"

TABLA_REGEX = re.compile(r"\b(Tabla\s+\d+(?:[.-]\d+)+)\b", re.IGNORECASE)
FIGURA_REGEX = re.compile(r"\b(Figura\s+\d+(?:[.-]\d+)+)\b", re.IGNORECASE)
GRAFICO_REGEX = re.compile(r"\b(Gr[aá]fico\s+\d+(?:[.-]\d+)+)\b", re.IGNORECASE)
NUMERAL_REGEX = re.compile(
    r"\b((?:Numeral\s+\d+(?:\.\d+)+)|(?:\d+(?:\.\d+){2,}))\b", re.IGNORECASE
)
HEADING_REGEX = re.compile(r"^\s*(\d+(?:\.\d+)+)\s+(.+)$")
NUM_HEADING_GLUE_REGEX = re.compile(r"^\s*(\d+(?:\.\d+){1,10})([A-ZÁÉÍÓÚÑ].+)$")
CAPITULO_REGEX = re.compile(r"^\s*cap[ií]tulo\s+[ivxlcdm\d]+\b", re.IGNORECASE)
TOC_ENTRY_PREFIX_REGEX = re.compile(
    r"^\s*(?:#{1,6}\s+)?(?P<entry>(?:Tabla|Figura|Gr[aá]fico)\s+\d+(?:[.-]\d+)+|(?:Numeral\s+)?\d+(?:\.\d+)+)\b",
    re.IGNORECASE,
)
TOC_PAGE_HINT_REGEX = re.compile(r"(?:\.{2,}|\s+\d+(?:\.\d+)*-\d+\s*$|\s+\d+\s*$)", re.IGNORECASE)
TOC_TITLE_MARKERS = ("tabla de contenidos", "contenido", "índice", "indice")
TOC_GLUE_LINE_REGEX = re.compile(r"^\s*\d+(?:\.\d+){1,10}[A-ZÁÉÍÓÚÑ].*\d+(?:\.\d+)*-\d+\s*$")


@dataclass
class Referenciable:
    archivo: str
    pagina: int
    tipo: str
    id_detectado: str
    titulo_o_contexto: str
    snippet: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Capa 2: PDF/DOCX -> Markdown + elementos referenciables")
    parser.add_argument("--input-dir", type=Path, required=True, help="Directorio con PDFs/DOCX de entrada")
    parser.add_argument("--output-dir", type=Path, default=Path("out/capa2"), help="Directorio de salida")
    parser.add_argument(
        "--ocr-engine",
        choices=["pypdf", "mistral"],
        default="pypdf",
        help="Motor OCR/texto para PDFs. `mistral` usa MISTRAL_API_KEY del entorno.",
    )
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


def extract_text_pages_mistral(pdf_path: Path) -> list[str]:
    """Extrae texto por página con Mistral OCR si hay API key configurada."""
    api_key = os.getenv("MISTRAL_API_KEY")
    if not api_key:
        raise RuntimeError("No se encontró MISTRAL_API_KEY en el entorno para usar OCR de Mistral.")

    try:
        from mistralai import Mistral  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "Dependencia faltante: instala `mistralai` (pip install mistralai) para usar OCR de Mistral."
        ) from exc

    client = Mistral(api_key=api_key)
    with pdf_path.open("rb") as f:
        uploaded = client.files.upload(file={"file_name": pdf_path.name, "content": f}, purpose="ocr")

    signed = client.files.get_signed_url(file_id=uploaded.id)
    time.sleep(0.5)
    ocr_response = client.ocr.process(
        model="mistral-ocr-latest",
        document={"type": "document_url", "document_url": signed.url},
    )

    return [normalize_text(page.markdown or "") for page in ocr_response.pages]


def extract_docx_pages(docx_path: Path) -> list[str]:
    """Extrae texto de DOCX como una sola "página" lógica."""
    with zipfile.ZipFile(docx_path) as zf:
        try:
            xml_content = zf.read("word/document.xml")
        except KeyError as exc:
            raise RuntimeError(f"DOCX inválido o dañado: {docx_path}") from exc

    root = ET.fromstring(xml_content)
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    paragraphs: list[str] = []

    for paragraph in root.findall(".//w:p", ns):
        runs = paragraph.findall(".//w:t", ns)
        text = "".join(run.text or "" for run in runs).strip()
        if text:
            paragraphs.append(text)

    return [normalize_text("\n".join(paragraphs))]


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
        page_lines = remove_toc_noise(page_text.split("\n"))
        for line in page_lines:
            chunks.append(format_heading_line(line))
    return "\n".join(chunks).strip() + "\n"


def format_heading_line(line: str) -> str:
    stripped = line.strip()
    if not stripped:
        return ""

    if CAPITULO_REGEX.match(stripped):
        return f"# {stripped}"

    glued = NUM_HEADING_GLUE_REGEX.match(stripped)
    if glued:
        stripped = f"{glued.group(1)} {glued.group(2).strip()}"

    m = HEADING_REGEX.match(stripped)
    if m:
        depth = min(6, max(3, len(m.group(1).split(".")) + 1))
        return f"{'#' * depth} {m.group(1)} {m.group(2).strip()}"

    return line


def remove_toc_noise(lines: list[str]) -> list[str]:
    """Descarta líneas de TOC para no convertirlas en headings del cuerpo."""
    if not lines:
        return lines

    if not is_likely_toc_page(lines):
        return lines

    cleaned: list[str] = []
    for line in lines:
        if TOC_ENTRY_PREFIX_REGEX.match(line) and TOC_PAGE_HINT_REGEX.search(line):
            continue
        if TOC_GLUE_LINE_REGEX.match(line):
            continue
        cleaned.append(line)
    return cleaned


def is_likely_toc_page(lines: list[str]) -> bool:
    normalized = [ln.strip().lower() for ln in lines if ln.strip()]
    if not normalized:
        return False

    has_toc_marker = any(any(marker in ln for marker in TOC_TITLE_MARKERS) for ln in normalized)
    toc_entries = sum(
        1
        for ln in lines
        if (TOC_ENTRY_PREFIX_REGEX.match(ln) and TOC_PAGE_HINT_REGEX.search(ln)) or TOC_GLUE_LINE_REGEX.match(ln)
    )
    dotted_lines = sum(1 for ln in lines if re.search(r"\.{2,}\s*\d+\s*$", ln))

    if toc_entries >= 4:
        return True
    if has_toc_marker and toc_entries >= 2:
        return True
    if dotted_lines >= 6 and toc_entries >= 2:
        return True
    return False


def detect_referenciables(page_text: str, page_number: int, source_name: str) -> list[Referenciable]:
    results: list[Referenciable] = []
    toc_lines = [
        line
        for line in page_text.split("\n")
        if TOC_ENTRY_PREFIX_REGEX.match(line) and TOC_PAGE_HINT_REGEX.search(line)
    ]

    if not toc_lines:
        return results

    for toc_line in toc_lines:
        entry = TOC_ENTRY_PREFIX_REGEX.match(toc_line).group("entry")  # type: ignore[union-attr]

        def add_matches(pattern: re.Pattern[str], tipo: str) -> None:
            for match in pattern.finditer(entry):
                snippet = toc_line.strip()
                results.append(
                    Referenciable(
                        archivo=source_name,
                        pagina=page_number,
                        tipo=tipo,
                        id_detectado=match.group(1),
                        titulo_o_contexto=context_from_snippet(snippet),
                        snippet=snippet,
                    )
                )

        entry_lower = entry.lower().strip()
        add_matches(TABLA_REGEX, "tabla")
        add_matches(FIGURA_REGEX, "figura")
        add_matches(GRAFICO_REGEX, "figura")
        if not entry_lower.startswith(("tabla", "figura", "gráfico", "grafico")):
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


def process_document(doc_path: Path, output_dir: Path, ocr_engine: str = "pypdf") -> tuple[Path, Path, int]:
    if doc_path.suffix.lower() == ".pdf":
        pages = extract_text_pages_mistral(doc_path) if ocr_engine == "mistral" else extract_text_pages(doc_path)
    elif doc_path.suffix.lower() == ".docx":
        pages = extract_docx_pages(doc_path)
    else:
        raise RuntimeError(f"Formato no soportado en Capa 2: {doc_path.name}")

    markdown = pages_to_markdown(pages, doc_path.name)

    elementos: list[Referenciable] = []
    for i, page_text in enumerate(pages, start=1):
        elementos.extend(detect_referenciables(page_text, i, doc_path.name))

    md_path = output_dir / "markdown" / f"{doc_path.stem}.md"
    csv_path = output_dir / "elementos" / f"{doc_path.stem}_elementos.csv"
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

    supported = sorted(
        [p for p in input_dir.iterdir() if p.is_file() and p.suffix.lower() in {".pdf", ".docx"}]
    )
    if not supported:
        print(f"ERROR: no se encontraron archivos soportados (.pdf/.docx) en {input_dir}")
        return 2

    unsupported_docs = sorted([p.name for p in input_dir.iterdir() if p.is_file() and p.suffix.lower() == ".doc"])
    if unsupported_docs:
        print(f"AVISO: archivos .doc no soportados en Capa 2 (omitiendo): {', '.join(unsupported_docs)}")

    total_elements = 0
    for doc in supported:
        md, csv_path, count = process_document(doc, output_dir, ocr_engine=args.ocr_engine)
        total_elements += count
        print(f"OK: {doc.name} -> {md} | {csv_path} | elementos={count}")

    print(f"Resumen: documentos={len(supported)} elementos={total_elements} output={output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
