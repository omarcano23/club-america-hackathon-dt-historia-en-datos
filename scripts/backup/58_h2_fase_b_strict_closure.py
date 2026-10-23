"""
Paso 58 (Fase B - Cierre Estricto y Validación de Muestra):
Refinamiento del denominador excluyendo Out y Pass Offside, y validación estricta de la muestra.
Proyecto: El Vuelo del Bicampeón (ISAC 2026)
"""

from pathlib import Path
import pandas as pd
import json

DATA_DIR = Path(r"C:\Users\omarc\AI_Projects\Competitions\club-america-isac-2026\data")
PROCESSED_DIR = DATA_DIR / "processed"

def strict_closure_phase_b():
    print("===================================================================")
    print("🔬 FASE B: CIERRE ESTRICTO Y VALIDACIÓN DOCUMENTADA DEL DENOMINADOR")
    print("==================================================================-\n")

    events_file = PROCESSED_DIR / "events_master.csv"
    summary_file = PROCESSED_DIR / "h2_resumen_ppda_r10.csv"

    if not events_file.exists() or not summary_file.exists():
        print("❌ Error: Faltan archivos requeridos en processed/.")
        return

    df_ev = pd.read_csv(events_file, low_memory=False)
    df_summary = pd.read_csv(summary_file)

    df_ev["match_id_clean"] = pd.to_numeric(
        df_ev["match_id"].astype(str).str.replace("match_", ""),
        errors="coerce"
    ).fillna(-1).astype("int64")

    valid_match_ids = set(df_summary["match_id"])
    df_match_ev = df_ev[df_ev["match_id_clean"].isin(valid_match_ids)].copy()

    # Selección espacial validada por G3: X >= 80 para eventos rivales
    df_rival_att3rd = df_match_ev[
        (~df_match_ev["is_america_action"]) & 
        (df_match_ev["location_x"] >= 80) &
        (df_match_ev["period"] <= 4)
    ].copy()

    strict_restarts = ["From Corner", "From Free Kick", "From Goal Kick", "From Kick Off", "From Throw In"]
    # Definición estricta: solo Miscontrol, Dispossessed y pases Incomplete en juego abierto
    valid_pass_outcomes = ["Incomplete"]

    def classify_loss_strict_v2(row):
        pp = row["play_pattern"]
        if pp in strict_restarts:
            return "EXCLUIDO_REINICIO_ESTATICO"
        
        t = row["type"]
        po = row["pass_outcome"]

        if t in ["Miscontrol", "Dispossessed"]:
            return "VALIDO_JUEGO_ABIERTO"
        
        if t == "Pass":
            if pd.isna(po):
                return "EXCLUIDO_PASE_COMPLETADO"
            po_str = str(po).strip()
            if po_str in valid_pass_outcomes:
                return "VALIDO_JUEGO_ABIERTO"
            else:
                return f"EXCLUIDO_OTRO_OUTCOME_{po_str}"

        return "EXCLUIDO_OTRO_TIPO"

    df_rival_att3rd["clasificacion_estricta"] = df_rival_att3rd.apply(classify_loss_strict_v2, axis=1)

    print("1. Desglose de Clasificación Estricta (Fase B Refinada):")
    print("-" * 65)
    counts_strict = df_rival_att3rd["clasificacion_estricta"].value_counts().reset_index(name="count")
    print(counts_strict.to_string(index=False))

    df_valido = df_rival_att3rd[df_rival_att3rd["clasificacion_estricta"] == "VALIDO_JUEGO_ABIERTO"].copy()
    print(f"\n2. Nuevo Denominador Estricto Congelado: {len(df_valido):,} pérdidas elegibles.")

    # Exportar lista inmutable para la Fase C
    universe_path = PROCESSED_DIR / "h2_denominador_congelado_v2.csv"
    df_valido[["match_id", "event_id", "type", "pass_outcome", "play_pattern", "location_x", "location_y", "period", "minute", "second"]].to_csv(universe_path, index=False)
    print(f"3. Archivo del universo congelado guardado en: {universe_path.name}")

    print("\n===================================================================")
    print("✅ FASE B CERRADA BAJO CRITERIO ESTRICTO.")
    print("==================================================================-\n")

if __name__ == "__main__":
    strict_closure_phase_b()