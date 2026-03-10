#!/usr/bin/env python3
"""Capa 1 - Ingesta de documentos para QA de referencias EIA.

Uso rápido:
    python src/capa1_ingesta.py --source /ruta/a/insumos

También puedes editar la constante DEFAULT_SOURCE_PATH para dejar una ruta fija.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import re
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

# Ruta editable por el usuario si no quiere usar --source
DEFAULT_SOURCE_PATH = ""

EXPECTED_CHAPTERS = tuple(f"cap{i}" for i in range(1, 8))
ALLOWED_EXTENSIONS = {".pdf", ".doc", ".docx"}
CHAPTER_PATTERN = re.compile(r"^(cap[1-7])(?:_v(\d+))?$", re.IGNORECASE)
CSV_ENCODING = "utf-8-sig"


@dataclass
class FileRecord:
    source_path: Path
    dest_path: Path
    file_name: str
    chapter: str | None
    declared_version: str | None
    extension: str
    size_bytes: int
    modified_at: str
    sha256: str
    name_status: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingesta de PDFs/Word para pipeline EIA")
    parser.add_argument(
        "--source",
        type=Path,
        default=Path(DEFAULT_SOURCE_PATH) if DEFAULT_SOURCE_PATH else None,
        help="Ruta de carpeta con insumos (PDF, DOC, DOCX).",
    )
    parser.add_argument(
        "--workspace",
        type=Path,
        default=Path("."),
        help="Directorio base donde crear input/ y out/. Por defecto: actual.",
    )
    parser.add_argument(
        "--lote",
        type=str,
        default=datetime.now().strftime("%Y%m%d_%H%M%S"),
        help="Nombre de lote. Ej: 20260131_101500",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Falla si falta algún capítulo esperado cap1..cap7.",
    )
    return parser.parse_args()


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            block = f.read(chunk_size)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def classify_filename(stem: str) -> tuple[str | None, str | None, str]:
    """Devuelve (capítulo, versión, estado_nombre)."""
    match = CHAPTER_PATTERN.match(stem)
    if not match:
        return None, None, "NOMBRE_NO_ESTANDAR"

    chapter = match.group(1).lower()
    version = match.group(2)
    return chapter, version, "OK"


def collect_input_files(source_dir: Path) -> list[Path]:
    files = [p for p in source_dir.iterdir() if p.is_file() and p.suffix.lower() in ALLOWED_EXTENSIONS]
    return sorted(files)


def ensure_dirs(base_workspace: Path, lote: str) -> tuple[Path, Path]:
    input_lote = base_workspace / "input" / f"lote_{lote}"
    out_lote = base_workspace / "out" / f"lote_{lote}"
    input_lote.mkdir(parents=True, exist_ok=True)
    out_lote.mkdir(parents=True, exist_ok=True)
    return input_lote, out_lote


def ingest_files(source_files: Iterable[Path], input_lote_dir: Path) -> list[FileRecord]:
    records: list[FileRecord] = []

    for src in source_files:
        chapter, version, name_status = classify_filename(src.stem)

        if chapter:
            target_name = f"{chapter}{src.suffix.lower()}"
        else:
            target_name = src.name.lower()

        dest = input_lote_dir / target_name
        shutil.copy2(src, dest)

        stat = dest.stat()
        record = FileRecord(
            source_path=src.resolve(),
            dest_path=dest.resolve(),
            file_name=dest.name,
            chapter=chapter,
            declared_version=version,
            extension=dest.suffix.lower(),
            size_bytes=stat.st_size,
            modified_at=datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
            sha256=sha256_file(dest),
            name_status=name_status,
        )
        records.append(record)

    return records


def strict_validation(records: Iterable[FileRecord]) -> list[str]:
    chapters_found = {r.chapter for r in records if r.chapter}
    missing = [c for c in EXPECTED_CHAPTERS if c not in chapters_found]
    return missing


def write_manifest(out_lote_dir: Path, lote: str, records: list[FileRecord]) -> Path:
    manifest_path = out_lote_dir / "ingesta_manifest.csv"
    with manifest_path.open("w", encoding=CSV_ENCODING, newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "lote",
                "source_path",
                "dest_path",
                "file_name",
                "chapter",
                "declared_version",
                "extension",
                "size_bytes",
                "modified_at",
                "sha256",
                "name_status",
            ]
        )
        for r in records:
            writer.writerow(
                [
                    lote,
                    str(r.source_path),
                    str(r.dest_path),
                    r.file_name,
                    r.chapter or "",
                    r.declared_version or "",
                    r.extension,
                    r.size_bytes,
                    r.modified_at,
                    r.sha256,
                    r.name_status,
                ]
            )
    return manifest_path


def main() -> int:
    args = parse_args()

    if args.source is None:
        print("ERROR: debes indicar --source o configurar DEFAULT_SOURCE_PATH en el script.")
        return 2

    source_dir = args.source.expanduser().resolve()
    workspace = args.workspace.expanduser().resolve()

    if not source_dir.exists() or not source_dir.is_dir():
        print(f"ERROR: ruta de entrada inválida: {source_dir}")
        return 2

    source_files = collect_input_files(source_dir)
    if not source_files:
        print(f"ERROR: no se encontraron archivos {sorted(ALLOWED_EXTENSIONS)} en {source_dir}")
        return 2

    input_lote_dir, out_lote_dir = ensure_dirs(workspace, args.lote)
    records = ingest_files(source_files, input_lote_dir)

    missing = strict_validation(records)
    if args.strict and missing:
        print(f"ERROR: faltan capítulos esperados: {', '.join(missing)}")
        return 1

    manifest_path = write_manifest(out_lote_dir, args.lote, records)

    print("Ingesta completada")
    print(f"- Lote: {args.lote}")
    print(f"- Archivos ingestados: {len(records)}")
    print(f"- Carpeta destino: {input_lote_dir}")
    print(f"- Manifest: {manifest_path}")

    if missing:
        print(f"- Aviso: faltan capítulos: {', '.join(missing)}")

    non_standard = [r.file_name for r in records if r.name_status != "OK"]
    if non_standard:
        print(f"- Aviso: nombres no estándar detectados: {', '.join(non_standard)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
