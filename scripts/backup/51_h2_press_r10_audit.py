"""
Paso 51 (Definitivo): Cálculo de PPDA y Tasa R10 condicional para la Hipótesis 2
Proyecto: El Vuelo del Bicampeón (ISAC 2026)
"""

from pathlib import Path
import pandas as pd
import numpy as np

DATA_DIR = Path(r"C:\Users\omarc\AI_Projects\Competitions\club-america-isac-2026\data")
PROCESSED_DIR = DATA_DIR / "processed"

def run_h2_rigorous_audit():
    print("===================================================================")
    print("🔬 AUDITORÍA H2: CÁLCULO DE PPDA Y TASA R10 CONDICIONADA")
    print("==================================================================-\n")

    matches_file = PROCESSED_DIR / "fase3_metricas_matches_master.csv"
    events_file = PROCESSED_DIR / "events_master.csv"

    if not matches_file.exists() or not events_file.exists():
        print("❌ Error: Faltan archivos maestros en processed/.")
        return

    df_matches = pd.read_csv(matches_file)
    df_ev = pd.read_csv(events_file, low_memory=False)
    
    # Limpieza de match_id
    df_ev["match_id_clean"] = pd.to_numeric(
        df_ev["match_id"].astype(str).str.replace("match_", ""),
        errors="coerce"
    ).fillna(-1).astype("int64")

    print(f"📋 Partidos en tabla maestra: {len(df_matches)}")
    print("1. Calculando PPDA por partido a partir de events_master...")

    # 1. Calcular PPDA por partido de forma robusta
    ppda_records = []
    
    for m_id, group in df_ev.groupby("match_id_clean"):
        if m_id == -1:
            continue
            
        # Pases rivales en zona defensiva del rival / propia del América (X <= 60)
        rival_passes = group[
            (~group["is_america_action"]) & 
            (group["type"] == "Pass") & 
            (group["location_x"] <= 60) &
            (group["period"] <= 4)
        ]
        
        # Acciones defensivas del América en campo rival (X >= 60)
        ame_def = group[
            (group["is_america_action"]) & 
            (group["location_x"] >= 60) & 
            (group["type"].isin(["Tackle", "Interception", "Foul Committed", "Duel", "Block"])) &
            (group["period"] <= 4)
        ].drop_duplicates(subset=["period", "minute", "second", "location_x", "location_y"])

        p_count = len(rival_passes)
        d_count = len(ame_def)
        
        ppda_val = (p_count / d_count) if d_count > 0 else np.nan
        
        ppda_records.append({
            "match_id": m_id,
            "pases_riv": p_count,
            "acciones_def": d_count,
            "ppda": ppda_val
        })

    df_ppda = pd.DataFrame(ppda_records)
    df_merged = pd.merge(df_matches, df_ppda, on="match_id", how="inner")
    
    median_ppda = df_merged["ppda"].median()
    df_merged["high_press_match"] = df_merged["ppda"] <= median_ppda

    print(f"   • Mediana de PPDA Calculada: {median_ppda:.2f}")

    # 2. Rastrear transiciones defensivas R10 (ventana de 10s tras pérdida rival en X >= 80)
    print("2. Procesando transiciones defensivas R10 (ventana de 10 segundos)...")
    
    loss_events = ["Miscontrol", "Dispossessed"]
    recovery_events = ["Tackle", "Interception", "Ball Recovery"]
    
    event_records = []
    match_summary = []

    for m_id, group in df_ev.groupby("match_id_clean"):
        match_subset = df_merged[df_merged["match_id"] == m_id]
        if match_subset.empty:
            continue
            
        match_meta = match_subset.iloc[0]
        match_ppda = match_meta["ppda"]
        high_press = match_meta["high_press_match"]

        group = group.sort_values(by=["period", "minute", "second"]).reset_index(drop=True)

        # Pérdidas rivales en el último tercio (X >= 80)
        rival_losses = group[
            (~group["is_america_action"]) & 
            (
                group["type"].isin(loss_events) | 
                ((group["type"] == "Pass") & (group["pass_outcome"].notna()))
            ) &
            (group["location_x"] >= 80) &
            (group["period"] <= 4)
        ]

        eligible_losses = len(rival_losses)
        r10_recoveries = 0

        for _, loss_row in rival_losses.iterrows():
            l_period = loss_row["period"]
            l_min = loss_row["minute"]
            l_sec = loss_row["second"]
            l_id = loss_row["event_id"]
            l_x = loss_row["location_x"]
            l_y = loss_row["location_y"]

            time_limit_sec = (l_min * 60 + l_sec) + 10.0

            subsequent_events = group[
                (group["period"] == l_period) & 
                ((group["minute"] * 60 + group["second"]) >= (l_min * 60 + l_sec)) &
                ((group["minute"] * 60 + group["second"]) <= time_limit_sec) &
                (group["is_america_action"])
            ]

            recovered = False
            rec_event_id = None
            elapsed_time = None

            for _, rec_row in subsequent_events.iterrows():
                if rec_row["type"] in recovery_events:
                    recovered = True
                    r10_recoveries += 1
                    rec_event_id = rec_row["event_id"]
                    elapsed_time = (rec_row["minute"] * 60 + rec_row["second"]) - (l_min * 60 + l_sec)
                    break

            event_records.append({
                "match_id": m_id,
                "loss_event_id": l_id,
                "period": l_period,
                "minute": l_min,
                "second": l_sec,
                "location_x": l_x,
                "location_y": l_y,
                "r10_success": int(recovered),
                "recovery_event_id": rec_event_id,
                "elapsed_seconds": elapsed_time,
                "ppda": match_ppda,
                "high_press_match": high_press
            })

        match_summary.append({
            "match_id": m_id,
            "ppda": match_ppda,
            "high_press_match": high_press,
            "eligible_losses": eligible_losses,
            "r10_recoveries": r10_recoveries,
            "tasa_r10": (r10_recoveries / eligible_losses) if eligible_losses > 0 else 0.0
        })

    df_events_out = pd.DataFrame(event_records)
    df_summary_out = pd.DataFrame(match_summary)

    # Exportar archivos de trazabilidad
    events_csv_path = PROCESSED_DIR / "h2_perdidas_r10_eventos.csv"
    summary_csv_path = PROCESSED_DIR / "h2_resumen_ppda_r10.csv"

    df_events_out.to_csv(events_csv_path, index=False)
    df_summary_out.to_csv(summary_csv_path, index=False)

    print(f"\n3. Archivos de trazabilidad guardados en processed/:")
    print(f"   • {events_csv_path.name} ({len(df_events_out):,} eventos de pérdida)")
    print(f"   • {summary_csv_path.name} ({len(df_summary_out)} partidos analizados)")

    # 4. Estadísticas agregadas
    high_group = df_summary_out[df_summary_out["high_press_match"]]
    low_group = df_summary_out[~df_summary_out["high_press_match"]]

    print("\n4. Resultados de Tasa R10 por Estrato de PPDA:")
    print(f"   • Partidos con Alta Presión (PPDA <= {median_ppda:.2f}):")
    print(f"     - Total Pérdidas Elegibles: {high_group['eligible_losses'].sum():,}")
    print(f"     - Total Recuperaciones R10: {high_group['r10_recoveries'].sum():,}")
    print(f"     - Tasa R10 Agregada: {(high_group['r10_recoveries'].sum() / high_group['eligible_losses'].sum() * 100):.2f}%" if high_group['eligible_losses'].sum() > 0 else "N/A")

    print(f"   • Partidos con Baja Presión (PPDA > {median_ppda:.2f}):")
    print(f"     - Total Pérdidas Elegibles: {low_group['eligible_losses'].sum():,}")
    print(f"     - Total Recuperaciones R10: {low_group['r10_recoveries'].sum():,}")
    print(f"     - Tasa R10 Agregada: {(low_group['r10_recoveries'].sum() / low_group['eligible_losses'].sum() * 100):.2f}%" if low_group['eligible_losses'].sum() > 0 else "N/A")

    print("\n===================================================================")
    print("✅ AUDITORÍA H2 EJECUTADA CON ÉXITO Y TRAZABILIDAD COMPLETA.")
    print("===================================================================")

if __name__ == "__main__":
    run_h2_rigorous_audit()