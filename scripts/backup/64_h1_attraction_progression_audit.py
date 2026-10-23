"""
Paso 64: Auditoría Falsable de Hipótesis H1 (Atracción y Progresión)
Evaluación de H1a (Circulación), H1b (Estructura 360) y H1c (Tasa de Éxito Comparada)

Proyecto: El Vuelo del Bicampeón (ISAC 2026)
"""

from pathlib import Path
import json
import pandas as pd
import numpy as np

DATA_DIR = Path(r"C:\Users\omarc\AI_Projects\Competitions\club-america-isac-2026\data")
PROCESSED_DIR = DATA_DIR / "processed"

def run_h1_audit():
    print("===================================================================")
    print("🔬 AUDITORÍA METODOLÓGICA DE HIPÓTESIS H1: ATRACCIÓN Y PROGRESIÓN")
    print("==================================================================-\n")

    events_file = PROCESSED_DIR / "events_master.csv"
    summary_file = PROCESSED_DIR / "h2_resumen_ppda_r10.csv"

    if not events_file.exists():
        print("❌ Error: events_master.csv no existe en processed/.")
        return

    df_ev = pd.read_csv(events_file, low_memory=False)

    # Filtrar solo los 66 partidos válidos de Fase Regular
    valid_match_ids = set()
    if summary_file.exists():
        df_sum = pd.read_csv(summary_file)
        valid_match_ids = set(df_sum["match_id"])

    df_match = df_ev[df_ev["match_id"].isin(valid_match_ids)].copy() if valid_match_ids else df_ev.copy()

    # Pases de América en juego abierto
    open_passes = df_match[
        (df_match["is_america_action"]) & 
        (df_match["type"] == "Pass") & 
        (df_match["pass_outcome"].isna() | (df_match["pass_outcome"] == "Recovery")) &
        (df_match["play_pattern"].isin(["Regular Play", "From Counter", "From Keeper"]))
    ].copy()

    # Clasificación de carril por coordenadas Y (24 a 56 es carril central)
    open_passes["carril_origen"] = np.where(
        (open_passes["location_y"] >= 24) & (open_passes["location_y"] <= 56), "CENTRAL", "EXTERIOR"
    )
    open_passes["carril_destino"] = np.where(
        (open_passes["end_location_y"] >= 24) & (open_passes["end_location_y"] <= 56), "CENTRAL", "EXTERIOR"
    )

    # --- H1a: Circulación Central -> Exterior ---
    open_passes["is_central_to_exterior"] = (open_passes["carril_origen"] == "CENTRAL") & (open_passes["carril_destino"] == "EXTERIOR")
    open_passes["is_in_build_up_zone"] = open_passes["location_x"] <= 60

    build_up_passes = open_passes[open_passes["is_in_build_up_zone"]].copy()
    total_bu_passes = len(build_up_passes)
    central_to_ext_passes = build_up_passes["is_central_to_exterior"].sum()
    pct_h1a = (central_to_ext_passes / total_bu_passes * 100) if total_bu_passes > 0 else 0.0

    print("1. EVALUACIÓN H1a (Circulación Central -> Exterior en Salida X <= 60):")
    print(f"   • Total de pases de salida en juego abierto: {total_bu_passes:,}")
    print(f"   • Pases de origen central -> destino exterior: {central_to_ext_passes:,} ({pct_h1a:.2f}%)")
    print(f"   • Veredicto H1a: {'CONFIRMADA' if pct_h1a >= 20.0 else 'DESECHADA / LÍNEA BASE BAJA'}\n")

    # --- H1c: Comparación de Éxito de Progresión (Entradas a X >= 80) ---
    bu_passes_prog = build_up_passes[build_up_passes["end_location_x"] >= 80]
    
    rate_central_ext = (build_up_passes[build_up_passes["is_central_to_exterior"]]["end_location_x"] >= 80).mean() * 100
    rate_direct_ext = (build_up_passes[~build_up_passes["is_central_to_exterior"]]["end_location_x"] >= 80).mean() * 100

    diff_pp = rate_central_ext - rate_direct_ext

    print("2. EVALUACIÓN H1c (Tasa de Progresión Directa a Último Tercio X >= 80):")
    print(f"   • Tasa de progresión tras pase Central -> Exterior: {rate_central_ext:.2f}%")
    print(f"   • Tasa de progresión en otras secuencias de salida: {rate_direct_ext:.2f}%")
    print(f"   • Diferencia en puntos porcentuales: {diff_pp:+.2f} pp")
    print(f"   • Veredicto H1c: {'VENTAJA DETECTADA' if diff_pp > 0 else 'SIN VENTAJA DEMOSTRADA'}\n")

    # Exportación del reporte H1
    h1_report = {
        "h1a_circulacion": {
            "total_pases_salida": total_bu_passes,
            "pases_central_a_exterior": int(central_to_ext_passes),
            "porcentaje": round(pct_h1a, 2),
            "cumple_criterio": bool(pct_h1a >= 20.0)
        },
        "h1c_progresion_efectiva": {
            "tasa_central_exterior_pct": round(rate_central_ext, 2),
            "tasa_otras_rutas_pct": round(rate_direct_ext, 2),
            "diferencia_pp": round(diff_pp, 2),
            "ventaja_demostrada": bool(diff_pp > 0)
        }
    }

    out_json = PROCESSED_DIR / "h1_evaluacion_falsable.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(h1_report, f, indent=4, ensure_ascii=False)

    print(f"✅ Archivo exportado: {out_json.name}")
    print("===================================================================")

if __name__ == "__main__":
    run_h1_audit()