"""
Paso 53 (Fase B - Versión 2): Auditoría Exhaustiva del Universo de Pérdidas Rival
Proyecto: El Vuelo del Bicampeón (ISAC 2026)
"""

from pathlib import Path
import pandas as pd
import json

DATA_DIR = Path(r"C:\Users\omarc\AI_Projects\Competitions\club-america-isac-2026\data")
PROCESSED_DIR = DATA_DIR / "processed"

def audit_loss_universe_v2():
    print("===================================================================")
    print("🔬 FASE B (ORDEN 2 - V2): AUDITORÍA EXHAUSTIVA DE PÉRDIDAS RIVALES")
    print("===================================================================\n")

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

    # Usar location_x directamente según la convención del proyecto (sin inversión no validada)
    df_rival_att3rd = df_match_ev[
        (~df_match_ev["is_america_action"]) & 
        (df_match_ev["location_x"] >= 80) &
        (df_match_ev["period"] <= 4)
    ].copy()

    print(f"1. Total eventos del rival con location_x >= 80 en los 66 partidos: {len(df_rival_att3rd):,}")

    # Desglose completo (sin truncar) de pass_outcome y play_pattern
    print("\n2. Desglose completo de pass_outcome por tipo y patrón de juego:")
    print("-" * 65)
    
    pd.set_option('display.max_rows', None)
    full_breakdown = df_rival_att3rd.groupby(["type", "pass_outcome", "play_pattern"], dropna=False).size().reset_index(name="count")
    full_breakdown = full_breakdown.sort_values(by="count", ascending=False)
    print(full_breakdown.to_string(index=False))

    # Identificar valores únicos de pass_outcome presentes
    unique_pass_outcomes = df_rival_att3rd["pass_outcome"].dropna().unique()
    print(f"\n3. Valores únicos de pass_outcome en el último tercio rival: {list(unique_pass_outcomes)}")

    # Clasificación formal por reglas de juego abierto vs reinicios
    restart_patterns = ["From Corner", "From Free Kick", "From Throw In", "From Kick Off", "From Goal Kick"]
    loss_types = ["Miscontrol", "Dispossessed"]

    # Candidatos por tipo estricto
    df_rival_att3rd["is_candidate_type"] = (
        df_rival_att3rd["type"].isin(loss_types) | 
        ((df_rival_att3rd["type"] == "Pass") & (df_rival_att3rd["pass_outcome"].notna()))
    )

    df_rival_att3rd["is_restart"] = df_rival_att3rd["play_pattern"].isin(restart_patterns)

    print("\n4. Resumen de Clasificación:")
    summary_counts = df_rival_att3rd.groupby(["is_candidate_type", "is_restart", "play_pattern"], dropna=False).size().reset_index(name="count")
    print(summary_counts.to_string(index=False))

    # Exportar muestra de eventos detallados para revisión manual
    sample_columns = ["match_id", "event_id", "type", "pass_outcome", "play_pattern", "team", "location_x", "location_y", "period", "minute", "second"]
    sample_export = df_rival_att3rd[df_rival_att3rd["is_candidate_type"] & (~df_rival_att3rd["is_restart"])][sample_columns].head(100)
    
    sample_path = PROCESSED_DIR / "h2_muestra_candidatos_perdidas.csv"
    sample_export.to_csv(sample_path, index=False)

    print(f"\n5. Muestra de 100 candidatos de juego abierto guardada en: {sample_path.name}")

    audit_data = {
        "fase": "Fase B - Auditoría Completa del Universo de Pérdidas",
        "pass_outcomes_unicos": list(unique_pass_outcomes),
        "total_eventos_rival_ultimo_tercio": int(len(df_rival_att3rd)),
        "candidatos_juego_abierto": int((df_rival_att3rd["is_candidate_type"] & (~df_rival_att3rd["is_restart"])).sum()),
        "candidatos_reinicios": int((df_rival_att3rd["is_candidate_type"] & (df_rival_att3rd["is_restart"])).sum())
    }

    report_path = PROCESSED_DIR / "h2_fase_b_auditoria_completa.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(audit_data, f, indent=4, ensure_ascii=False)

    print(f"6. Reporte JSON guardado en: {report_path.name}")
    print("===================================================================")
    print("✅ FASE B (ORDEN 2 - V2) COMPLETADA EXITOSAMENTE.")
    print("===================================================================\n")

if __name__ == "__main__":
    audit_loss_universe_v2()