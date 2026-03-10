# Opciones para acelerar el control de calidad de referencias entre capítulos de EIA

## Objetivo
Reducir el tiempo de revisión de referencias cruzadas (tablas, figuras, numerales, ítems) entre 7 capítulos PDF de un EIA, especialmente para mantener actualizado el capítulo 7 cuando cambian capítulos previos.

## Propuesta objetivo: arquitectura en 6 capas

### Capa 1. Ingesta de documentos
**Objetivo:** recibir los PDFs de entrada y organizarlos de forma consistente.

**Tareas clave**
- Validar nombres esperados (`cap1.pdf` ... `cap7.pdf`) y versión (`_vNN`).
- Mover archivos a una estructura estable:
  - `input/lote_YYYYMMDD/cap1.pdf` ... `cap7.pdf`
- Generar metadatos por archivo: hash, fecha, tamaño, versión declarada.

**Salida de la capa**
- `out/ingesta_manifest.csv` con trazabilidad de archivos.

### Capa 2. Extracción estructural (PDF -> Markdown)
**Objetivo:** transformar cada PDF a markdown con estructura utilizable.

#### 2.1 Extracción de texto y bloques
- Extraer texto por página y bloques (encabezados, párrafos, tablas, pies de figura).
- Aplicar OCR cuando el PDF sea escaneado.
- Conservar coordenadas mínimas (página/bbox) para evidencia.

#### 2.2 Detección de elementos referenciables
- Detectar y etiquetar:
  - Tablas (`Tabla 2-14`)
  - Figuras (`Figura 3-2`)
  - Numerales/secciones (`7.3.1`, `Numeral 4.2`)
  - Anexos/ítems si aplica
- Capturar `id`, `título/encabezado`, `página` y `snippet`.

**Salida de la capa**
- `out/markdown/capN.md`
- `out/elementos/capN_elementos.csv`

### Capa 3. Normalización e indexación
**Objetivo:** construir un índice maestro consultable con lo extraído de capítulos 1–6.

**Tareas clave**
- Normalizar formatos de IDs (`Tabla 2.14` -> `Tabla 2-14`).
- Homologar tipos (`item` vs `ítem`, `seccion` vs `sección`).
- Crear un índice maestro con claves técnicas estables.

**Campos recomendados del índice maestro**
- `capitulo`, `tipo`, `id_normalizado`, `id_original`, `titulo`, `pagina`, `hash_texto`, `version`.

**Salida de la capa**
- `out/indice/indice_maestro.parquet` (o `.csv` si priorizas simplicidad).

### Capa 4. Extracción de referencias desde capítulo 7
**Objetivo:** leer capítulo 7 y detectar todas las referencias cruzadas a capítulos previos.

**Tareas clave**
- Detectar menciones con regex + reglas de contexto.
- Extraer referencia explícita y ubicación en cap7 (página/párrafo).
- Clasificar referencia por tipo y capítulo objetivo.

**Ejemplos de patrones**
- `Tabla\s+\d+[.-]\d+`
- `Figura\s+\d+[.-]\d+`
- `Numeral\s+\d+(\.\d+)*`

**Salida de la capa**
- `out/referencias_cap7.csv`

### Capa 5. Matching y validación
**Objetivo:** comparar cada referencia de capítulo 7 contra el índice maestro (capítulos 1–6).

**Reglas de validación recomendadas**
- `OK`: referencia existe y coincide en tipo + ID.
- `ERROR_NO_EXISTE`: ID no aparece en índice maestro.
- `REVISAR_RENUMERACION`: no existe ID exacto, pero hay candidato similar por título.
- `REVISAR_TITULO`: existe ID, pero título cambió sobre umbral de similitud.
- `AMBIGUA`: múltiples candidatos plausibles.

**Técnicas útiles**
- Matching exacto por `tipo + id_normalizado`.
- Fuzzy matching de título (`rapidfuzz`) para renumeraciones.

**Salida de la capa**
- `out/validacion_resultados.csv`

### Capa 6. Reporte de control de calidad (Excel)
**Objetivo:** presentar resultados de forma revisable para cierre operativo.

**Estructura recomendada de Excel**
- Hoja 1 `resumen`: totales por estado y por capítulo.
- Hoja 2 `detalle`: una fila por referencia detectada en cap7.
- Hoja 3 `renumeraciones_sugeridas`: pares ID antiguo/nuevo.
- Hoja 4 `trazabilidad`: lote, versión, fecha y hash.

**Salida de la capa**
- `out/reporte_qa.xlsx`
- (Opcional) `out/reporte_qa.html` para visualización rápida.

---

## Opciones de implementación sobre la arquitectura

## Opción 1 (rápida): Validador automático por reglas + Excel/CSV
- Implementa primero capas 1, 4, 5 y 6 con extracción mínima.
- Ideal para entregar valor en poco tiempo.

## Opción 2 (recomendada): Índice automático + comparador de versiones
- Implementa completo 1 a 6.
- Añade comparación `versión_anterior` vs `versión_nueva` para detectar renumeraciones y cambios reales.

## Opción 3: LLM como auditor semántico (híbrido)
- Se monta encima de capas 4 y 5 para priorizar observaciones y proponer redacción de correcciones.
- Mantener capa 5 como “fuente de verdad” determinística.

## Opción 4: Flujo documental automatizado (SharePoint/Drive)
- Orquesta capas 1 a 6 cada vez que se sube una nueva versión.
- Publica automáticamente `reporte_qa.xlsx` para revisión del equipo.

---

## Roadmap sugerido
1. **Semana 1-2:** capas 1, 4, 5, 6 (MVP operativo).
2. **Semana 3-4:** capas 2 y 3 robustas + comparador de versiones.
3. **Semana 5+:** integración LLM para priorización semántica y apoyo de redacción.

## KPI para medir mejora
- % reducción de horas por ciclo de actualización.
- # errores de referencia detectados antes de entrega.
- Tiempo promedio de cierre de observaciones.
- % referencias con validación automática `OK` sin intervención manual.

## Recomendación final
Para tu caso, la mejor relación impacto/esfuerzo es:
- Empezar con la arquitectura de 6 capas en versión MVP (1, 4, 5, 6).
- Evolucionar a pipeline completo (1–6) con comparador de versiones.
- Agregar LLM después, como capa de productividad y no como validador principal.


## Implementación inicial disponible (Capa 1)
Se implementó el script `src/capa1_ingesta.py` para ejecutar la ingesta.

**Ejemplo de uso**
```bash
python src/capa1_ingesta.py --source /ruta/a/insumos --workspace . --lote 20260309_100000
```

**Comportamiento**
- Acepta archivos `.pdf`, `.doc` y `.docx`.
- Copia insumos al lote `input/lote_<id>/`.
- Genera `out/lote_<id>/ingesta_manifest.csv` con hash y metadatos.
- En modo `--strict`, falla si faltan capítulos `cap1..cap7`.


## Implementación inicial disponible (Capa 2)
Se implementó el script `src/capa2_extraccion_estructural.py` para la extracción estructural (PDF -> Markdown).

**Ejemplo de uso**
```bash
python src/capa2_extraccion_estructural.py --input-dir input/lote_20260309_100000 --output-dir out/capa2
```

**Salidas generadas**
- `out/capa2/markdown/<archivo>.md`
- `out/capa2/elementos/<archivo>_elementos.csv`

**Notas técnicas**
- El módulo 2.1 usa `pypdf` para extraer texto por página.
- El módulo 2.2 detecta `Tabla`, `Figura` y `Numeral` con regex.


## Implementación inicial disponible (Capa 3)
Se implementó el script `src/capa3_normalizacion_indexacion.py` para construir el índice maestro desde los CSV de Capa 2.

**Ejemplo de uso**
```bash
python src/capa3_normalizacion_indexacion.py --elementos-dir out/capa2/elementos --output-dir out/indice --version v12
```

**Salidas generadas**
- `out/indice/indice_maestro.csv`

**Comportamiento**
- Normaliza tipos e IDs detectados.
- Deduplica registros repetidos por `capitulo + tipo + id_normalizado + pagina`.
- Por defecto indexa capítulos `cap1..cap6` (usar `--include-cap7` para incluir capítulo 7).


## Implementación inicial disponible (Capa 4)
Se implementó el script `src/capa4_extraccion_referencias_cap7.py` para extraer referencias cruzadas desde capítulo 7.

**Ejemplo de uso**
```bash
python src/capa4_extraccion_referencias_cap7.py --cap7-file out/capa2/markdown/cap7.md --output-csv out/referencias_cap7.csv
```

**Salidas generadas**
- `out/referencias_cap7.csv`

**Comportamiento**
- Detecta `Tabla`, `Figura` y `Numeral` (con o sin palabra "Numeral").
- Identifica capítulo objetivo (`cap1..cap6`) desde el prefijo numérico.
- Normaliza IDs para la capa de matching (`Tabla 2-14`, `Figura 3-2`, `4-1-3`).
- Incluye contexto textual y deduplicación por página/párrafo/referencia.


## Implementación inicial disponible (Capa 5)
Se implementó el script `src/capa5_matching_validacion.py` para comparar referencias de cap7 contra el índice maestro.

**Ejemplo de uso**
```bash
python src/capa5_matching_validacion.py --indice out/indice/indice_maestro.csv --referencias out/referencias_cap7.csv --output-csv out/validacion_resultados.csv
```

**Salidas generadas**
- `out/validacion_resultados.csv`

**Estados de validación**
- `OK`: match exacto por tipo+ID y similitud de contexto/título sobre umbral.
- `REVISAR_TITULO`: ID exacto pero similitud baja.
- `REVISAR_RENUMERACION`: sin ID exacto, con candidato similar.
- `AMBIGUA`: múltiples candidatos cercanos.
- `ERROR_NO_EXISTE`: sin match exacto ni candidato similar.


## Implementación inicial disponible (Capa 6)
Se implementó el script `src/capa6_reporte_control_calidad.py` para generar el reporte final en Excel.

**Ejemplo de uso**
```bash
python src/capa6_reporte_control_calidad.py --validacion-csv out/validacion_resultados.csv --manifest-csv out/lote_20260309_100000/ingesta_manifest.csv --output-xlsx out/reporte_qa.xlsx
```

**Salidas generadas**
- `out/reporte_qa.xlsx`

**Hojas incluidas**
- `resumen`: conteo por estado y por capítulo objetivo.
- `detalle`: todas las referencias validadas.
- `renumeraciones_sugeridas`: recomendaciones para actualización en cap7.
- `trazabilidad`: metadatos de generación y lote de ingesta (si se provee manifest).

**Nota técnica**
- Requiere `openpyxl` para escribir `.xlsx`.

## Ejecución unificada del pipeline (capas 1 a 6)
Se agregó el script `src/orquestador_pipeline.py` para correr todas las capas en secuencia.

**Ejemplo de uso**
```bash
python src/orquestador_pipeline.py --source /ruta/a/insumos --workspace . --lote 20260310_120000 --version v1 --strict
```

**Parámetros útiles**
- `--capa2-output-dir`: personaliza salida de la capa 2.
- `--cap7-file`: usa un archivo de capítulo 7 específico para capa 4.
- `--umbral-similitud`: ajusta umbral de matching en capa 5.
- `--include-cap7-index`: incluye cap7 en índice maestro (capa 3).
