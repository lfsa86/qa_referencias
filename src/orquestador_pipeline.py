#!/usr/bin/env python3
"""Orquestador del pipeline QA de referencias (capas 1 a 6).

Ejemplo:
    python src/orquestador_pipeline.py --source /ruta/a/insumos --workspace . --lote 20260310_120000 --version v1
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class PipelinePaths:
    input_lote_dir: Path
    out_lote_dir: Path
    capa2_out_dir: Path
    indice_csv: Path
    referencias_csv: Path
    validacion_csv: Path
    reporte_xlsx: Path
    manifest_csv: Path
    cap7_markdown: Path


REPO_ROOT = Path(__file__).resolve().parent.parent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Orquestador pipeline QA de referencias (capas 1..6)")
    parser.add_argument("--source", type=Path, required=True, help="Carpeta con insumos de entrada (cap1..cap7)")
    parser.add_argument("--workspace", type=Path, default=Path("."), help="Directorio base de trabajo")
    parser.add_argument(
        "--lote",
        type=str,
        default=datetime.now().strftime("%Y%m%d_%H%M%S"),
        help="Identificador de lote (ej: 20260310_120000)",
    )
    parser.add_argument("--version", type=str, default="v1", help="Versión para índice maestro (Capa 3)")
    parser.add_argument(
        "--capa2-output-dir",
        type=Path,
        default=None,
        help="Directorio de salida de capa 2 (por defecto: <workspace>/out/capa2/lote_<id>)",
    )
    parser.add_argument(
        "--cap7-file",
        type=Path,
        default=None,
        help="Ruta markdown/txt para Capa 4. Por defecto: salida de Capa 2 en markdown/cap7.md",
    )
    parser.add_argument("--umbral-similitud", type=float, default=0.75, help="Umbral de similitud para Capa 5")
    parser.add_argument(
        "--include-cap7-index",
        action="store_true",
        help="Incluye cap7 al construir índice maestro en Capa 3",
    )
    parser.add_argument("--strict", action="store_true", help="Activa --strict en Capa 1")
    return parser.parse_args()


def build_paths(workspace: Path, lote: str, capa2_output_dir: Path | None, cap7_file: Path | None) -> PipelinePaths:
    ws = workspace.resolve()
    input_lote_dir = ws / "input" / f"lote_{lote}"
    out_lote_dir = ws / "out" / f"lote_{lote}"
    capa2_out_dir = capa2_output_dir.resolve() if capa2_output_dir else ws / "out" / "capa2" / f"lote_{lote}"

    indice_csv = ws / "out" / "indice" / "indice_maestro.csv"
    referencias_csv = ws / "out" / "referencias_cap7.csv"
    validacion_csv = ws / "out" / "validacion_resultados.csv"
    reporte_xlsx = ws / "out" / "reporte_qa.xlsx"
    manifest_csv = out_lote_dir / "ingesta_manifest.csv"
    cap7_markdown = cap7_file.resolve() if cap7_file else capa2_out_dir / "markdown" / "cap7.md"

    return PipelinePaths(
        input_lote_dir=input_lote_dir,
        out_lote_dir=out_lote_dir,
        capa2_out_dir=capa2_out_dir,
        indice_csv=indice_csv,
        referencias_csv=referencias_csv,
        validacion_csv=validacion_csv,
        reporte_xlsx=reporte_xlsx,
        manifest_csv=manifest_csv,
        cap7_markdown=cap7_markdown,
    )


def run_step(step_name: str, cmd: list[str]) -> None:
    print(f"\n=== {step_name} ===")
    print("$", " ".join(cmd))
    subprocess.run(cmd, check=True, cwd=REPO_ROOT)


def main() -> int:
    args = parse_args()
    source = args.source.expanduser().resolve()
    workspace = args.workspace.expanduser().resolve()

    if not source.exists() or not source.is_dir():
        print(f"ERROR: source inválido: {source}")
        return 2

    paths = build_paths(workspace, args.lote, args.capa2_output_dir, args.cap7_file)

    py = sys.executable
    capa1_cmd = [
        py,
        str(REPO_ROOT / "src" / "capa1_ingesta.py"),
        "--source",
        str(source),
        "--workspace",
        str(workspace),
        "--lote",
        args.lote,
    ]
    if args.strict:
        capa1_cmd.append("--strict")

    capa2_cmd = [
        py,
        str(REPO_ROOT / "src" / "capa2_extraccion_estructural.py"),
        "--input-dir",
        str(paths.input_lote_dir),
        "--output-dir",
        str(paths.capa2_out_dir),
    ]

    capa3_cmd = [
        py,
        str(REPO_ROOT / "src" / "capa3_normalizacion_indexacion.py"),
        "--elementos-dir",
        str(paths.capa2_out_dir / "elementos"),
        "--output-dir",
        str(paths.indice_csv.parent),
        "--version",
        args.version,
    ]
    if args.include_cap7_index:
        capa3_cmd.append("--include-cap7")

    capa4_cmd = [
        py,
        str(REPO_ROOT / "src" / "capa4_extraccion_referencias_cap7.py"),
        "--cap7-file",
        str(paths.cap7_markdown),
        "--output-csv",
        str(paths.referencias_csv),
    ]

    capa5_cmd = [
        py,
        str(REPO_ROOT / "src" / "capa5_matching_validacion.py"),
        "--indice",
        str(paths.indice_csv),
        "--referencias",
        str(paths.referencias_csv),
        "--output-csv",
        str(paths.validacion_csv),
        "--umbral-similitud",
        str(args.umbral_similitud),
    ]

    capa6_cmd = [
        py,
        str(REPO_ROOT / "src" / "capa6_reporte_control_calidad.py"),
        "--validacion-csv",
        str(paths.validacion_csv),
        "--manifest-csv",
        str(paths.manifest_csv),
        "--output-xlsx",
        str(paths.reporte_xlsx),
    ]

    try:
        run_step("Capa 1 - Ingesta", capa1_cmd)
        run_step("Capa 2 - Extracción estructural", capa2_cmd)
        run_step("Capa 3 - Normalización e indexación", capa3_cmd)
        run_step("Capa 4 - Extracción referencias cap7", capa4_cmd)
        run_step("Capa 5 - Matching y validación", capa5_cmd)
        run_step("Capa 6 - Reporte QA", capa6_cmd)
    except subprocess.CalledProcessError as exc:
        print(f"\nERROR: falló el paso con código {exc.returncode}")
        return exc.returncode

    print("\nPipeline completado.")
    print(f"- Manifest: {paths.manifest_csv}")
    print(f"- Índice: {paths.indice_csv}")
    print(f"- Referencias cap7: {paths.referencias_csv}")
    print(f"- Validación: {paths.validacion_csv}")
    print(f"- Reporte: {paths.reporte_xlsx}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
