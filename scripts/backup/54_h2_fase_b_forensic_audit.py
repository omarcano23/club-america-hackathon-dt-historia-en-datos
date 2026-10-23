"""
Paso 54 (Fase B - Auditoría Forense Definitiva): Validación del Universo de Pérdidas y Pass Outcomes
Proyecto: El Vuelo del Bicampeón (ISAC 2026)
"""

from pathlib import Path
import pandas as pd
import json

DATA_DIR = Path(r"C:\Users\omarc\AI_Projects\Competitions\club-america-isac-2026\data")
PROCESSED_DIR = DATA_DIR / "processed"

def run_fase_b_forensic_audit():
    print("===================================================================")
    print("🔬 FASE B: AUDITORÍA FORENSE DEL UNIVERSO DE PÉRDIDAS RIVALES")
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

    # 1. Validación espacial: confirmación de la convención nativa en events_master.csv
    # En events_master.csv, las coordenadas ya vienen normalizadas por posesión según el pipeline congelado de Fase 3.
    # Por tanto, evaluamos location_x >= 80 directamente sin inversiones no justificadas.
    df_rival_att3rd = df_match_ev[
        (~df_match_ev["is_america_action"]) & 
        (df_match_ev["location_x"] >= 80) &
        (df_match_ev["period"] <= 4)
    ].copy()

    print(f"1. Total de eventos rivales con location_x >= 80 en los 66 partidos: {len(df_rival_att3rd):,}")

    # 2. Análisis detallado de pass_outcome para pases en el último tercio
    passes_in_zone = df_rival_att3rd[df_rival_att3rd["type"] == "Pass"]
    print("\n2. Desglose completo de pass_outcome en pases rivales (X >= 80):")
    print("-" * 65)
    pass_outcomes_counts = passes_in_zone["pass_outcome"].value_counts(dropna=False)
    print(pass_outcomes_counts.to_string())

    # 3. Clasificación y Decisión Metodológica por tipo y play_pattern
    # Definir patrones de reinicio estáticos a excluir
    strict_restarts = ["From Corner", "From Free Kick", "From Goal Kick", "From Kick Off", "From Throw In"]
    
    # Patrones de juego abierto o transición a conservar (Regular Play, From Counter, From Keeper, Other)
    # Nota: From Counter y From Keeper se mantienen porque provienen de flujo dinámico/juego abierto.

    def classify_loss_event(row):
        t = row["type"]
        po = row["pass_outcome"]
        pp = row["play_pattern"]

        # Si es un reinicio estático, se excluye del denominador de juego abierto
        if pp in strict_restarts:
            return "EXCLUIDO_REINICIO_ESTATICO"

        # Tipos base directos de pérdida
        if t in ["Miscontrol", "Dispossessed"]:
            return "INCLUIR_PERDIDA_DIRECTA"

        # Pases en zona
        if t == "Pass":
            if pd.isna(po):
                return "EXCLUIDO_PASE_COMPLETADO"
            
            # Evaluar subtipos de pass_outcome
            po_str = str(po).strip()
            if po_str in ["Incomplete", "Out", "Pass Offside"]:
                return "INCLUIR_PASE_FALLIDO"
            elif po_str in ["Unknown", "Injury Clearance"]:
                return "EXCLUIDO_ANOMALIA_O_INTERRUPCION"
            else:
                return f"REVISION_MANUAL_{po_str}"

        return "EXCLUIDO_OTRO_TIPO"

    df_rival_att3rd["decision_categoria"] = df_rival_att3rd.apply(classify_loss_event, axis=1)

    print("\n3. Tabla de Decisiones y Conteos del Universo Rival (X >= 80):")
    print("-" * 65)
    decision_summary = df_rival_att3rd["decision_categoria"].value_counts().reset_index(name="count")
    print(decision_summary.to_string(index=False))

    # Filtrar estrictamente los elegibles válidos (pases fallidos netos + miscontrol + dispossessed en juego abierto)
    eligible_df = df_rival_att3rd[df_rival_att3rd["decision_categoria"].isin([
        "INCLUIR_PERDIDA_DIRECTA", "INCLUIR_PASE_FALLIDO"
    ])].copy()

    print(f"\n4. Total de pérdidas elegibles validadas en juego abierto: {len(eligible_df):,}")

    # Exportar muestra detallada de 150 casos para auditoría manual
    sample_cols = ["match_id", "event_id", "type", "pass_outcome", "play_pattern", "team", "location_x", "location_y", "period", "minute", "second", "decision_categoria"]
    sample_export = eligible_df[sample_cols].head(150)
    sample_path = PROCESSED_DIR / "h2_fase_b_candidatos_validados.csv"
    sample_export.to_csv(sample_path, index=False)

    print(f"5. Muestra de candidatos validados guardada en: {sample_path.name}")

    # Guardar reporte JSON de Fase B
    fase_b_report = {
        "fase": "Fase B - Auditoría y Cierre del Universo de Pérdidas",
        "total_eventos_rival_zona": int(len(df_rival_att3rd)),
        "desglose_decisiones": decision_summary.set_index("decision_categoria")["count"].to_dict(),
        "total_candidatos_validos": int(len(eligible_df)),
        "estado": "Completado y Documentado"
    }

    report_path = PROCESSED_DIR / "h2_fase_b_reporte_cierre.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(fase_b_report, f, indent=4, ensure_ascii=False)

    print(f"6. Reporte de cierre de Fase B guardado en: {report_path.name}")
    print("===================================================================")
    print("✅ FASE B COMPLETADA Y DOCUMENTADA RIGUROSAMENTE.")
    print("==================================================================-\n")

if __name__ == "__main__":
    run_fase_b_forensic_audit()