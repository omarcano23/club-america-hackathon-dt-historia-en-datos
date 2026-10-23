
#!/usr/bin/env python3
"""Valida la estructura de web_data.json sin modificar archivos."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "report" / "web_data.json"

REQUIRED_SECTIONS = {
    "capitulo_1_identidad",
    "capitulo_2_progresion",
    "capitulo_3_recuperacion",
    "capitulo_4_contexto",
    "capitulo_5_balon_parado",
}

def main():
    if not DATA_FILE.exists():
        print(f"ERROR: No existe {DATA_FILE}")
        print("Comprueba la ruta del JSON antes de continuar.")
        sys.exit(1)

    try:
        with DATA_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as exc:
        print(f"ERROR: JSON no válido: {exc}")
        sys.exit(1)

    metadata = data.get("metadata", {})
    print("=== VALIDACIÓN DE WEB_DATA.JSON ===")
    print(f"Archivo: {DATA_FILE}")
    print(f"Versión declarada: {metadata.get('version', 'No indicada')}")
    print(f"Partidos totales: {metadata.get('matches_total', 'No indicado')}")
    print(f"Fase regular: {metadata.get('fase_regular_matches', 'No indicado')}")

    missing = REQUIRED_SECTIONS - data.keys()

    if missing:
        print("\nERROR: Faltan capítulos:")
        for section in sorted(missing):
            print(f"  - {section}")
        sys.exit(1)

    print("\nCapítulos encontrados:")
    for section in sorted(REQUIRED_SECTIONS):
        content = data[section]
        question = content.get("pregunta", "(sin pregunta)")
        print(f"  OK {section}: {question}")

    print("\nEstados de las métricas:")
    for section in sorted(REQUIRED_SECTIONS):
        content = data[section]
        metrics = content.get("kpis") or content.get("h2_r10") or \
                  content.get("gamestate") or content.get("abp_stats") or {}

        if not isinstance(metrics, dict):
            continue

        for name, metric in metrics.items():
            if isinstance(metric, dict):
                status = metric.get("estado", content.get("estado", "Sin estado"))
                print(f"  {section}.{name}: {status}")

    print("\nVALIDACIÓN ESTRUCTURAL COMPLETADA.")
    print("Esto no certifica la validez estadística de las métricas.")

if __name__ == "__main__":
    main()
