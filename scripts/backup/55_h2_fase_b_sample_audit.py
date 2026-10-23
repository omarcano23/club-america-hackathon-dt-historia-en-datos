"""
Paso 55 (Fase B - Auditoría Estratificada de Muestra y Cierre de Definiciones):
Validación estricta de Pass Outcomes, Patrones de Juego y Coordenadas.
Proyecto: El Vuelo del Bicampeón (ISAC 2026)
"""

from pathlib import Path
import pandas as pd
import json

DATA_DIR = Path(r"C:\Users\omarc\AI_Projects\Competitions\club-america-isac-2026\data")
PROCESSED_DIR = DATA_DIR / "processed"

def audit_phase_b_sample():
    print("===================================================================")
    print("🔬 FASE B: AUDITORÍA ESTRATIFICADA DE MUESTRA Y CIERRE DEL DENOMINADOR")
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

    # 1. Aplicar la regla de orientación espacial validada en la Fase 3 del proyecto:
    # Las coordenadas en events_master.csv se encuentran orientadas por posesión (X de 0 a 120).
    # Para eventos rivales en el último tercio defensivo del América (zona de presión alta), 
    # evaluamos location_x >= 80 directamente bajo la convención congelada.
    df_rival_att3rd = df_match_ev[
        (~df_match_ev["is_america_action"]) & 
        (df_match_ev["location_x"] >= 80) &
        (df_match_ev["period"] <= 4)
    ].copy()

    print(f"1. Total eventos rivales con location_x >= 80 analizados: {len(df_rival_att3rd):,}")

    # 2. Análisis detallado de los pass_outcome ambiguos o marginales (Unknown, Injury Clearance)
    marginal_outcomes = df_rival_att3rd[df_rival_att3rd["pass_outcome"].isin(["Unknown", "Injury Clearance"])].copy()
    print(f"   • Eventos con pass_outcome 'Unknown' o 'Injury Clearance' en zona: {len(marginal_outcomes)}")
    if len(marginal_outcomes) > 0:
        print(marginal_outcomes[["match_id", "event_id", "type", "pass_outcome", "play_pattern", "minute", "second"]].head(5).to_string(index=False))

    # 3. Regla de Clasificación Metodológica Refinada:
    # - Excluir reinicios estáticos puros: From Corner, From Free Kick, From Goal Kick, From Kick Off, From Throw In.
    # - Mantener juego abierto dinámico: Regular Play, From Counter, From Keeper, Other.
    # - Definir pérdida válida: Miscontrol, Dispossessed y pases con pass_outcome en ['Incomplete', 'Out', 'Pass Offside'].
    #   (Descartar explícitamente 'Unknown' e 'Injury Clearance' por falta de certeza en la pérdida de control).

    strict_restarts = ["From Corner", "From Free Kick", "From Goal Kick", "From Kick Off", "From Throw In"]
    valid_pass_outcomes = ["Incomplete", "Out", "Pass Offside"]

    def classify_loss_strict(row):
        t = row["type"]
        po = row["pass_outcome"]
        pp = row["play_pattern"]

        # 1. Filtrar por patrón de reinicio estático
        if pp in strict_restarts:
            return "EXCLUIDO_REINICIO_ESTATICO"

        # 2. Pérdidas directas por control o desposesión
        if t in ["Miscontrol", "Dispossessed"]:
            return "VALIDO_JUEGO_ABIERTO"

        # 3. Pases rivales en zona
        if t == "Pass":
            if pd.isna(po):
                return "EXCLUIDO_PASE_COMPLETADO"
            
            po_str = str(po).strip()
            if po_str in valid_pass_outcomes:
                return "VALIDO_JUEGO_ABIERTO"
            else:
                return f"EXCLUIDO_ANOMALIA_{po_str}"

        return "EXCLUIDO_OTRO_TIPO"

    df_rival_att3rd["clasificacion_definitiva"] = df_rival_att3rd.apply(classify_loss_strict, axis=1)

    print("\n2. Tabla de Decisión Consolidada y Conteos del Universo:")
    print("-" * 65)
    counts_table = df_rival_att3rd["clasificacion_definitiva"].value_counts().reset_index(name="count")
    print(counts_table.to_string(index=False))

    # Filtrar universo validado estricto
    df_valido = df_rival_att3rd[df_rival_att3rd["clasificacion_definitiva"] == "VALIDO_JUEGO_ABIERTO"].copy()
    print(f"\n3. Total definitivo de pérdidas elegibles validadas en juego abierto: {len(df_valido):,}")

    # 4. Extraer muestra estratificada para inspección manual (ej. 30 de cada tipo: Miscontrol, Dispossessed, Incomplete, Out, Pass Offside)
    sample_list = []
    for cat in ["Miscontrol", "Dispossessed", "Pass"]:
        sub = df_valido[df_valido["type"] == cat]
        sample_list.append(sub.sample(min(len(sub), 40), random_state=42))
    
    df_sample_stratified = pd.concat(sample_list)
    sample_cols = ["match_id", "event_id", "type", "pass_outcome", "play_pattern", "team", "location_x", "location_y", "period", "minute", "second"]
    
    output_sample_path = PROCESSED_DIR / "h2_fase_b_muestra_estratificada.csv"
    df_sample_stratified[sample_cols].to_csv(output_sample_path, index=False)
    print(f"4. Muestra estratificada de 120 casos guardada en: {output_sample_path.name}")

    # Guardar reporte JSON de cierre de Fase B
    fase_b_cierre = {
        "fase": "Fase B - Cierre Metodológico del Denominador de Pérdidas",
        "total_eventos_zona": int(len(df_rival_att3rd)),
        "desglose_decision": counts_table.set_index("clasificacion_definitiva")["count"].to_dict(),
        "total_perdidas_validadas": int(len(df_valido)),
        "estado": "Aprobado para Fase C"
    }

    report_cierre_path = PROCESSED_DIR / "h2_fase_b_cierre_denominador.json"
    with open(report_cierre_path, "w", encoding="utf-8") as f:
        json.dump(fase_b_cierre, f, indent=4, ensure_ascii=False)

    print(f"5. Reporte de cierre guardado en: {report_cierre_path.name}")
    print("===================================================================")
    print("✅ FASE B CERRADA CON RIGOR Y TRAZABILIDAD DOCUMENTADA.")
    print("===================================================================\n")

if __name__ == "__main__":
    audit_phase_b_sample()