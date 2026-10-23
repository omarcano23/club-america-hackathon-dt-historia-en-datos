"""
Paso 51 (Versión 4 - Corregida): Auditoría H2 con Control Bilateral y Ventana de 10s
Proyecto: El Vuelo del Bicampeón (ISAC 2026)
"""

from pathlib import Path
import pandas as pd
import numpy as np

DATA_DIR = Path(r"C:\Users\omarc\AI_Projects\Competitions\club-america-isac-2026\data")
PROCESSED_DIR = DATA_DIR / "processed"

def run_h2_v4_audit():
    print("===================================================================")
    print("🔬 AUDITORÍA H2-V4: SECUENCIA BILATERAL + VENTANA R10 ESTRICTA")
    print("===================================================================\n")

    matches_file = PROCESSED_DIR / "fase3_matches_master_unificado.csv"
    events_file = PROCESSED_DIR / "events_master.csv"

    if not matches_file.exists() or not events_file.exists():
        print("❌ Error: Faltan archivos maestros en processed/.")
        return

    df_matches = pd.read_csv(matches_file)
    df_ev = pd.read_csv(events_file, low_memory=False)
    
    df_ev["match_id_clean"] = pd.to_numeric(
        df_ev["match_id"].astype(str).str.replace("match_", ""),
        errors="coerce"
    ).fillna(-1).astype("int64")

    # 1. Validar columna PPDA oficial en tabla unificada
    if "ppda" not in df_matches.columns:
        raise KeyError("❌ La columna 'ppda' no se encuentra en fase3_matches_master_unificado.csv.")

    # Filtrar partidos de Fase Regular
    stage_lower = df_matches["stage"].astype(str).str.lower()
    reg_mask = (
        stage_lower.str.contains("apertura|clausura|regular") & 
        ~stage_lower.str.contains("quarter|semi|final|play-off|playoff|play_in|playin")
    )
    df_reg = df_matches[reg_mask].copy() if reg_mask.sum() > 0 else df_matches.copy()
    df_reg = df_reg.dropna(subset=["ppda"]).copy()

    median_ppda = df_reg["ppda"].median()
    df_reg["high_press_match"] = df_reg["ppda"] <= median_ppda

    print(f"1. Partidos de Fase Regular con PPDA oficial: {len(df_reg)}")
    print(f"   • Mediana de PPDA Oficial: {median_ppda:.2f}\n")

    # 2. Procesamiento transaccional riguroso (Ventana 10s + Control Bilateral)
    print("2. Ejecutando reconstrucción secuencial de transiciones defensivas R10...")
    
    loss_types = ["Miscontrol", "Dispossessed"]
    recovery_types = ["Tackle", "Interception", "Ball Recovery"]
    
    event_records = []
    match_summary = []

    for _, match_row in df_reg.iterrows():
        m_id = match_row["match_id"]
        match_ppda = match_row["ppda"]
        high_press = match_row["high_press_match"]

        match_events = df_ev[df_ev["match_id_clean"] == m_id].sort_values(by=["period", "index"]).reset_index(drop=True)
        if match_events.empty:
            continue

        # Normalización espacial simétrica (180°) para eventos del rival
        match_events["loc_x_norm"] = np.where(
            match_events["is_america_action"],
            match_events["location_x"],
            120.0 - match_events["location_x"]
        )
        match_events["loc_y_norm"] = np.where(
            match_events["is_america_action"],
            match_events["location_y"],
            80.0 - match_events["location_y"]
        )

        def get_abs_seconds(row):
            p = row["period"]
            m = row["minute"]
            s = row["second"]
            offset = 0
            if p == 2:
                offset = 2700  # 45 min
            elif p == 3:
                offset = 5400  # 90 min
            elif p == 4:
                offset = 6300  # 105 min
            return offset + (m * 60 + s)

        match_events["abs_time"] = match_events.apply(get_abs_seconds, axis=1)

        # Pérdidas rivales elegibles en el último tercio ofensivo del América (X_norm >= 80)
        rival_losses = match_events[
            (~match_events["is_america_action"]) & 
            (
                match_events["type"].isin(loss_types) | 
                ((match_events["type"] == "Pass") & (match_events["pass_outcome"].notna()))
            ) &
            (match_events["loc_x_norm"] >= 80) &
            (match_events["period"] <= 4)
        ]

        eligible_losses = 0
        r10_recoveries = 0
        used_recoveries = set()

        for _, loss_row in rival_losses.iterrows():
            eligible_losses += 1
            l_id = loss_row["event_id"]
            l_period = loss_row["period"]
            l_index = loss_row["index"]
            l_time = loss_row["abs_time"]
            l_x = loss_row["loc_x_norm"]
            l_y = loss_row["loc_y_norm"]

            subsequent = match_events[
                (match_events["period"] == l_period) & 
                (match_events["index"] > l_index)
            ]

            recovered = False
            rec_event_id = None
            elapsed_time = None
            outcome = "sin_recuperacion_en_ventana"
            exclusion_reason = None

            for _, sub_row in subsequent.iterrows():
                sub_time = sub_row["abs_time"]
                delta_t = sub_time - l_time

                if delta_t > 10.0:
                    exclusion_reason = "fuera_de_ventana_10s"
                    break

                if delta_t < 0:
                    continue

                # Control bilateral seguro con verificación de nulos en Pandas
                if not sub_row["is_america_action"]:
                    pass_outcome = sub_row.get("pass_outcome", np.nan)
                    is_pass_success = (sub_row["type"] == "Pass") and (pd.isna(pass_outcome) or pass_outcome == "")
                    
                    if is_pass_success:
                        exclusion_reason = "salida_exitosa_rival"
                        break
                    if sub_row["type"] in ["Foul Committed", "Out"]:
                        exclusion_reason = "interrupcion_juego"
                        break

                if sub_row["is_america_action"] and sub_row["type"] in recovery_types:
                    if sub_row["event_id"] not in used_recoveries:
                        recovered = True
                        r10_recoveries += 1
                        used_recoveries.add(sub_row["event_id"])
                        rec_event_id = sub_row["event_id"]
                        elapsed_time = delta_t
                        outcome = "r10_exitoso"
                        exclusion_reason = None
                        break

            event_records.append({
                "match_id": m_id,
                "loss_event_id": l_id,
                "recovery_event_id": rec_event_id,
                "loss_timestamp": l_time,
                "recovery_timestamp": (l_time + elapsed_time) if elapsed_time is not None else np.nan,
                "elapsed_seconds": elapsed_time,
                "r10_success": int(recovered),
                "outcome_type": outcome,
                "exclusion_reason": exclusion_reason,
                "location_x_norm": l_x,
                "location_y_norm": l_y,
                "ppda": match_ppda,
                "high_press_match": high_press
            })

        tasa_val = (r10_recoveries / eligible_losses) if eligible_losses > 0 else np.nan

        match_summary.append({
            "match_id": m_id,
            "ppda": match_ppda,
            "high_press_match": high_press,
            "eligible_losses": eligible_losses,
            "r10_recoveries": r10_recoveries,
            "tasa_r10": tasa_val
        })

    df_events_out = pd.DataFrame(event_records)
    df_summary_out = pd.DataFrame(match_summary)

    events_csv_path = PROCESSED_DIR / "h2_perdidas_r10_eventos.csv"
    summary_csv_path = PROCESSED_DIR / "h2_resumen_ppda_r10.csv"

    df_events_out.to_csv(events_csv_path, index=False)
    df_summary_out.to_csv(summary_csv_path, index=False)

    print(f"3. Archivos de trazabilidad guardados en processed/:")
    print(f"   • {events_csv_path.name} ({len(df_events_out):,} eventos transaccionales)")
    print(f"   • {summary_csv_path.name} ({len(df_summary_out)} partidos)\n")

    valid_summary = df_summary_out.dropna(subset=["tasa_r10"])
    high_group = valid_summary[valid_summary["high_press_match"]]
    low_group = valid_summary[~valid_summary["high_press_match"]]

    print("4. Resultados Consolidados (H2-V4 con Ventana Estricta y Control Bilateral):")
    print(f"   • Partidos con Alta Presión (PPDA <= {median_ppda:.2f}):")
    print(f"     - Partidos con oportunidades: {len(high_group)}")
    print(f"     - Total Pérdidas Elegibles: {high_group['eligible_losses'].sum():,}")
    print(f"     - Total Recuperaciones R10: {high_group['r10_recoveries'].sum():,}")
    print(f"     - Tasa R10 Agregada: {(high_group['r10_recoveries'].sum() / high_group['eligible_losses'].sum() * 100):.2f}%" if high_group['eligible_losses'].sum() > 0 else "N/A")

    print(f"\n   • Partidos con Baja Presión (PPDA > {median_ppda:.2f}):")
    print(f"     - Partidos con oportunidades: {len(low_group)}")
    print(f"     - Total Pérdidas Elegibles: {low_group['eligible_losses'].sum():,}")
    print(f"     - Total Recuperaciones R10: {low_group['r10_recoveries'].sum():,}")
    print(f"     - Tasa R10 Agregada: {(low_group['r10_recoveries'].sum() / low_group['eligible_losses'].sum() * 100):.2f}%" if low_group['eligible_losses'].sum() > 0 else "N/A")

    print("\n===================================================================")
    print("✅ AUDITORÍA H2-V4 FINALIZADA CON TRAZABILIDAD BILATERAL.")
    print("===================================================================\n")

if __name__ == "__main__":
    run_h2_v4_audit()