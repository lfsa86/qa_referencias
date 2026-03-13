#!/usr/bin/env python3
"""Capa 3 - Normalización e indexación.

Toma los CSV de elementos detectados en Capa 2 y construye un índice maestro consultable.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

CSV_ENCODING = "utf-8-sig"

TYPE_MAP = {
    "tabla": "tabla",
    "figura": "figura",
    "numeral": "numeral",
    "item": "item",
    "ítem": "item",
    "seccion": "seccion",
    "sección": "seccion",
}

CHAPTER_FROM_FILE = re.compile(r"(cap[1-7])", re.IGNORECASE)
CHAPTER_FROM_SECTION = re.compile(r"(?<!\d)([1-7])(?:[.-]\d+)+")


@dataclass
class IndexRow:
    capitulo: str
    tipo: str
    id_normalizado: str
    id_original: str
    titulo: str
    pagina: int
    hash_texto: str
    version: str
    archivo_origen: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Capa 3: normalización e indexación")
    parser.add_argument(
        "--elementos-dir",
        type=Path,
        default=Path("out/capa2/elementos"),
        help="Directorio con *_elementos.csv de Capa 2.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("out/indice"),
        help="Directorio de salida del índice maestro.",
    )
    parser.add_argument(
        "--version",
        type=str,
        default="v1",
        help="Versión documental asociada al índice (ej. v12).",
    )
    parser.add_argument(
        "--include-cap7",
        action="store_true",
        help="Incluye cap7. Por defecto solo indexa capítulos 1..6.",
    )
    return parser.parse_args()


def normalize_type(raw: str) -> str:
    key = raw.strip().lower()
    return TYPE_MAP.get(key, key)


def normalize_id(tipo: str, raw_id: str) -> str:
    text = " ".join(raw_id.strip().split())
    text = text.replace(".", "-")

    if tipo in {"tabla", "figura"}:
        text = re.sub(r"(?i)^tabla\s+", "Tabla ", text)
        text = re.sub(r"(?i)^figura\s+", "Figura ", text)
        return text

    if tipo == "numeral":
        text = re.sub(r"(?i)^numeral\s+", "", text)
        return text

    return text


def chapter_from_filename(name: str) -> str:
    m = CHAPTER_FROM_FILE.search(name)
    if not m:
        return "desconocido"
    return m.group(1).lower()


def chapter_from_reference(*values: str) -> str:
    for value in values:
        m = CHAPTER_FROM_SECTION.search(value or "")
        if m:
            return f"cap{m.group(1)}"
    return "desconocido"


def hash_text(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8")).hexdigest()


def load_element_rows(csv_path: Path, version: str) -> list[IndexRow]:
    rows: list[IndexRow] = []
    with csv_path.open("r", encoding=CSV_ENCODING, newline="") as f:
        reader = csv.DictReader(f)
        for raw in reader:
            tipo = normalize_type(raw.get("tipo", ""))
            id_original = (raw.get("id_detectado") or "").strip()
            id_norm = normalize_id(tipo, id_original)
            titulo = (raw.get("titulo_o_contexto") or "").strip()
            pagina = int(raw.get("pagina") or 0)
            archivo = (raw.get("archivo") or csv_path.name).strip()
            capitulo = chapter_from_filename(archivo)
            if capitulo == "desconocido":
                capitulo = chapter_from_reference(id_original, titulo)

            base_hash = "|".join([capitulo, tipo, id_norm, titulo])
            rows.append(
                IndexRow(
                    capitulo=capitulo,
                    tipo=tipo,
                    id_normalizado=id_norm,
                    id_original=id_original,
                    titulo=titulo,
                    pagina=pagina,
                    hash_texto=hash_text(base_hash),
                    version=version,
                    archivo_origen=archivo,
                )
            )
    return rows


def deduplicate(rows: Iterable[IndexRow]) -> list[IndexRow]:
    seen: set[tuple[str, str, str, int]] = set()
    out: list[IndexRow] = []
    for r in rows:
        key = (r.capitulo, r.tipo, r.id_normalizado, r.pagina)
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
    return out


def write_index_csv(output_csv: Path, rows: list[IndexRow]) -> None:
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", encoding=CSV_ENCODING, newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "capitulo",
                "tipo",
                "id_normalizado",
                "id_original",
                "titulo",
                "pagina",
                "hash_texto",
                "version",
                "archivo_origen",
            ]
        )
        for r in rows:
            writer.writerow(
                [
                    r.capitulo,
                    r.tipo,
                    r.id_normalizado,
                    r.id_original,
                    r.titulo,
                    r.pagina,
                    r.hash_texto,
                    r.version,
                    r.archivo_origen,
                ]
            )


def main() -> int:
    args = parse_args()
    elementos_dir = args.elementos_dir.resolve()
    output_dir = args.output_dir.resolve()

    if not elementos_dir.exists() or not elementos_dir.is_dir():
        print(f"ERROR: elementos-dir inválido: {elementos_dir}")
        return 2

    csv_files = sorted(elementos_dir.glob("*_elementos.csv"))
    if not csv_files:
        print(f"ERROR: no se encontraron *_elementos.csv en {elementos_dir}")
        return 2

    all_rows: list[IndexRow] = []
    for csv_path in csv_files:
        rows = load_element_rows(csv_path, args.version)
        all_rows.extend(rows)

    if not args.include_cap7:
        all_rows = [r for r in all_rows if r.capitulo in {f"cap{i}" for i in range(1, 7)}]

    all_rows = deduplicate(all_rows)
    all_rows.sort(key=lambda r: (r.capitulo, r.tipo, r.id_normalizado, r.pagina))

    output_csv = output_dir / "indice_maestro.csv"
    write_index_csv(output_csv, all_rows)

    print(f"Índice generado: {output_csv}")
    print(f"Registros: {len(all_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
