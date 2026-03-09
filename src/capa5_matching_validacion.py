#!/usr/bin/env python3
"""Capa 5 - Matching y validación.

Compara referencias detectadas en capítulo 7 contra el índice maestro (cap1..cap6)
y genera estados de validación para QA.
"""

from __future__ import annotations

import argparse
import csv
import difflib
from dataclasses import dataclass
from pathlib import Path


@dataclass
class IndexEntry:
    capitulo: str
    tipo: str
    id_normalizado: str
    id_original: str
    titulo: str
    pagina: int
    hash_texto: str
    version: str
    archivo_origen: str


@dataclass
class RefEntry:
    archivo: str
    pagina: int
    parrafo_idx: int
    tipo: str
    referencia_original: str
    capitulo_objetivo: str
    id_normalizado: str
    contexto: str


@dataclass
class ValidationRow:
    archivo_cap7: str
    pagina_cap7: int
    parrafo_idx: int
    tipo: str
    referencia_original: str
    capitulo_objetivo: str
    id_normalizado_ref: str
    estado: str
    detalle: str
    id_match: str
    titulo_match: str
    pagina_match: int
    similitud_titulo: float


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Capa 5: matching y validación")
    parser.add_argument("--indice", type=Path, default=Path("out/indice/indice_maestro.csv"), help="Índice maestro CSV")
    parser.add_argument(
        "--referencias",
        type=Path,
        default=Path("out/referencias_cap7.csv"),
        help="Referencias extraídas desde cap7 CSV",
    )
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=Path("out/validacion_resultados.csv"),
        help="Salida de resultados de validación",
    )
    parser.add_argument(
        "--umbral-similitud",
        type=float,
        default=0.75,
        help="Umbral para considerar candidato por título/contexto parecido.",
    )
    return parser.parse_args()


def _to_int(value: str | int | None) -> int:
    try:
        return int(value or 0)
    except ValueError:
        return 0


def load_index(path: Path) -> list[IndexEntry]:
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"Índice no encontrado: {path}")

    rows: list[IndexEntry] = []
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(
                IndexEntry(
                    capitulo=(r.get("capitulo") or "").strip(),
                    tipo=(r.get("tipo") or "").strip(),
                    id_normalizado=(r.get("id_normalizado") or "").strip(),
                    id_original=(r.get("id_original") or "").strip(),
                    titulo=(r.get("titulo") or "").strip(),
                    pagina=_to_int(r.get("pagina")),
                    hash_texto=(r.get("hash_texto") or "").strip(),
                    version=(r.get("version") or "").strip(),
                    archivo_origen=(r.get("archivo_origen") or "").strip(),
                )
            )
    return rows


def load_refs(path: Path) -> list[RefEntry]:
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"Referencias no encontradas: {path}")

    rows: list[RefEntry] = []
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(
                RefEntry(
                    archivo=(r.get("archivo") or "").strip(),
                    pagina=_to_int(r.get("pagina")),
                    parrafo_idx=_to_int(r.get("parrafo_idx")),
                    tipo=(r.get("tipo") or "").strip(),
                    referencia_original=(r.get("referencia_original") or "").strip(),
                    capitulo_objetivo=(r.get("capitulo_objetivo") or "").strip(),
                    id_normalizado=(r.get("id_normalizado") or "").strip(),
                    contexto=(r.get("contexto") or "").strip(),
                )
            )
    return rows


def ratio(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, (a or "").lower(), (b or "").lower()).ratio()


def validate_one(ref: RefEntry, index_rows: list[IndexEntry], threshold: float) -> ValidationRow:
    scope = [i for i in index_rows if i.capitulo == ref.capitulo_objetivo and i.tipo == ref.tipo]

    exact = [i for i in scope if i.id_normalizado == ref.id_normalizado]
    if len(exact) == 1:
        e = exact[0]
        sim = ratio(ref.contexto, e.titulo)
        state = "OK" if sim >= threshold else "REVISAR_TITULO"
        detail = "Coincidencia exacta por ID" if state == "OK" else "ID coincide pero título/contexto difiere"
        return ValidationRow(
            archivo_cap7=ref.archivo,
            pagina_cap7=ref.pagina,
            parrafo_idx=ref.parrafo_idx,
            tipo=ref.tipo,
            referencia_original=ref.referencia_original,
            capitulo_objetivo=ref.capitulo_objetivo,
            id_normalizado_ref=ref.id_normalizado,
            estado=state,
            detalle=detail,
            id_match=e.id_normalizado,
            titulo_match=e.titulo,
            pagina_match=e.pagina,
            similitud_titulo=round(sim, 4),
        )

    if len(exact) > 1:
        return ValidationRow(
            archivo_cap7=ref.archivo,
            pagina_cap7=ref.pagina,
            parrafo_idx=ref.parrafo_idx,
            tipo=ref.tipo,
            referencia_original=ref.referencia_original,
            capitulo_objetivo=ref.capitulo_objetivo,
            id_normalizado_ref=ref.id_normalizado,
            estado="AMBIGUA",
            detalle="Múltiples coincidencias exactas en el índice",
            id_match=ref.id_normalizado,
            titulo_match="",
            pagina_match=0,
            similitud_titulo=0.0,
        )

    # Sin match exacto: buscar candidato similar por contexto/título.
    scored: list[tuple[float, IndexEntry]] = []
    for candidate in scope:
        sim = ratio(ref.contexto, candidate.titulo)
        scored.append((sim, candidate))
    scored.sort(key=lambda x: x[0], reverse=True)

    if scored and scored[0][0] >= threshold:
        best_sim, best = scored[0]
        # Ambigüedad si top1 y top2 son muy cercanos
        if len(scored) > 1 and abs(scored[0][0] - scored[1][0]) < 0.03:
            return ValidationRow(
                archivo_cap7=ref.archivo,
                pagina_cap7=ref.pagina,
                parrafo_idx=ref.parrafo_idx,
                tipo=ref.tipo,
                referencia_original=ref.referencia_original,
                capitulo_objetivo=ref.capitulo_objetivo,
                id_normalizado_ref=ref.id_normalizado,
                estado="AMBIGUA",
                detalle="Sin match exacto; múltiples candidatos similares",
                id_match=best.id_normalizado,
                titulo_match=best.titulo,
                pagina_match=best.pagina,
                similitud_titulo=round(best_sim, 4),
            )

        return ValidationRow(
            archivo_cap7=ref.archivo,
            pagina_cap7=ref.pagina,
            parrafo_idx=ref.parrafo_idx,
            tipo=ref.tipo,
            referencia_original=ref.referencia_original,
            capitulo_objetivo=ref.capitulo_objetivo,
            id_normalizado_ref=ref.id_normalizado,
            estado="REVISAR_RENUMERACION",
            detalle="No existe ID exacto; candidato similar por título/contexto",
            id_match=best.id_normalizado,
            titulo_match=best.titulo,
            pagina_match=best.pagina,
            similitud_titulo=round(best_sim, 4),
        )

    return ValidationRow(
        archivo_cap7=ref.archivo,
        pagina_cap7=ref.pagina,
        parrafo_idx=ref.parrafo_idx,
        tipo=ref.tipo,
        referencia_original=ref.referencia_original,
        capitulo_objetivo=ref.capitulo_objetivo,
        id_normalizado_ref=ref.id_normalizado,
        estado="ERROR_NO_EXISTE",
        detalle="Sin coincidencia exacta ni candidato similar",
        id_match="",
        titulo_match="",
        pagina_match=0,
        similitud_titulo=0.0,
    )


def validate_all(refs: list[RefEntry], index_rows: list[IndexEntry], threshold: float) -> list[ValidationRow]:
    return [validate_one(ref, index_rows, threshold) for ref in refs]


def write_results(path: Path, rows: list[ValidationRow]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "archivo_cap7",
                "pagina_cap7",
                "parrafo_idx",
                "tipo",
                "referencia_original",
                "capitulo_objetivo",
                "id_normalizado_ref",
                "estado",
                "detalle",
                "id_match",
                "titulo_match",
                "pagina_match",
                "similitud_titulo",
            ]
        )
        for r in rows:
            w.writerow(
                [
                    r.archivo_cap7,
                    r.pagina_cap7,
                    r.parrafo_idx,
                    r.tipo,
                    r.referencia_original,
                    r.capitulo_objetivo,
                    r.id_normalizado_ref,
                    r.estado,
                    r.detalle,
                    r.id_match,
                    r.titulo_match,
                    r.pagina_match,
                    r.similitud_titulo,
                ]
            )


def summarize(rows: list[ValidationRow]) -> dict[str, int]:
    out: dict[str, int] = {}
    for r in rows:
        out[r.estado] = out.get(r.estado, 0) + 1
    return dict(sorted(out.items(), key=lambda kv: kv[0]))


def main() -> int:
    args = parse_args()

    try:
        index_rows = load_index(args.indice.resolve())
        refs = load_refs(args.referencias.resolve())
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}")
        return 2

    results = validate_all(refs, index_rows, args.umbral_similitud)
    write_results(args.output_csv.resolve(), results)

    print(f"Validaciones generadas: {len(results)}")
    print(f"Salida: {args.output_csv.resolve()}")
    print("Resumen por estado:")
    for state, count in summarize(results).items():
        print(f"- {state}: {count}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
