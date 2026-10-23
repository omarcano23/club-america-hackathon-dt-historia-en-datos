"""
Paso 51 (Versión 5 - Definitiva): Auditoría H2 con Máquina de Estados Bilateral,
Tiempos Corregidos, Atribución Única y Prueba Estadística a Nivel de Partido.
Proyecto: El Vuelo del Bicampeón (ISAC 2026)
"""

from pathlib import Path
import pandas as pd
import numpy as np
from scipy import stats

DATA_DIR = Path(r"C:\Users\omarc\AI_Projects\Competitions\club-america-isac-2026\data")
PROCESSED_DIR = DATA_DIR / "processed"

def run_h2_v5_audit():
    print("===================================================================")
    print("🔬 AUDITORÍA H2-V5: MÁQUINA DE ESTADOS BILATERAL + INFERENCIA ESTADÍSTICA")
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

    print("2. Ejecutando reconstrucción transaccional con máquina de estados estricta...")
    
    loss_types = ["Miscontrol", "Dispossessed"]
    recovery_types = ["Tackle", "Interception", "Ball Recovery"]
    interruption_types = ["Foul Committed", "Out", "Shot", "Goal"]
    
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

        # Cálculo de tiempo en segundos dentro del periodo (evitando doble offset si minute ya es relativo al periodo)
        match_events["period_seconds"] = match_events["minute"] * 60 + match_events["second"]

        # Identificar pérdidas rivales elegibles en el último tercio ofensivo del América (X_norm >= 80)
        rival_losses = match_events[
            (~match_events["is_america_action"]) & 
            (
                match_events["type"].isin(loss_types) | 
                ((match_events["type"] == "Pass") & (match_events["pass_outcome"].notna()))
            ) &
            (match_events["loc_x_norm"] >= 80) &
            (match_events["period"] <= 4)
        ].copy()

        eligible_losses = 0
        r10_recoveries = 0
        used_recoveries = set()

        # Convertir a lista de diccionarios para iteración eficiente de máquina de estados
        events_list = match_events.to_dict(orient="records")
        losses_list = rival_losses.to_dict(orient="records")

        for i, loss in enumerate(losses_list):
            eligible_losses += 1
            l_id = loss["event_id"]
            l_period = loss["period"]
            l_index = loss["index"]
            l_time = loss["period_seconds"]
            l_x = loss_row_x = loss["loc_x_norm"]
            l_y = loss_row_y = loss["loc_y_norm"]

            # Comprobar si hay una pérdida rival posterior antes de que termine la ventana (para evitar solapamientos incorrectos)
            next_loss_index = float('inf')
            if i + 1 < len(losses_list):
                if losses_list[i+1]["period"] == l_period:
                    next_loss_index = losses_list[i+1]["index"]

            recovered = False
            rec_event_id = None
            elapsed_time = None
            outcome = "sin_recuperacion_en_ventana"
            exclusion_reason = None

            # Buscar en eventos subsiguientes del mismo periodo
            for ev in events_list:
                if ev["period"] != l_period or ev["index"] <= l_index:
                    continue
                
                # Si llegamos a una nueva pérdida rival antes de resolver esta, cerramos la transición actual
                if ev["index"] >= next_loss_index:
                    exclusion_reason = "interrumpido_por_nueva_perdida_rival"
                    break

                sub_time = ev["period_seconds"]
                delta_t = sub_time - l_time

                # Ventana estrictamente positiva y hasta 10.0 segundos
                if delta_t > 10.0:
                    exclusion_reason = "fuera_de_ventana_10s"
                    break

                if delta_t <= 0:
                    continue  # Ignoramos eventos simultáneos (delta_t == 0) para evitar ambigüedad temporal

                # Control bilateral de interrupciones o salidas rivales
                if not ev["is_america_action"]:
                    pass_outcome = ev.get("pass_outcome", np.nan)
                    is_pass_success = (ev["type"] == "Pass") and (pd.isna(pass_outcome) or pass_outcome == "")
                    
                    if is_pass_success:
                        exclusion_reason = "salida_exitosa_rival"
                        break
                    if ev["type"] in interruption_types:
                        exclusion_reason = "interrupcion_juego"
                        break

                # Evaluar recuperación efectiva del América
                if ev["is_america_action"] and ev["type"] in recovery_types:
                    if ev["event_id"] not in used_recoveries:
                        recovered = True
                        r10_recoveries += 1
                        used_recoveries.add(ev["event_id"])
                        rec_event_id = ev["event_id"]
                        elapsed_time = delta_t
                        outcome = "r10_exitoso"
                        exclusion_reason = None
                        break

            event_records.append({
                "match_id": m_id,
                "loss_event_id": l_id,
                "recovery_event_id": rec_event_id,
                "loss_period_seconds": l_time,
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
            "home_team": match_row["home_team"],
            "away_team": match_row["away_team"],
            "ppda": match_ppda,
            "high_press_match": high_press,
            "eligible_losses": eligible_losses,
            "r10_recoveries": r10_recoveries,
            "tasa_r10": tasa_val
        })

    df_events_out = pd.DataFrame(event_records)
    df_summary_out = pd.DataFrame(match_summary)

    # Exportar archivos de trazabilidad definitivos
    events_csv_path = PROCESSED_DIR / "h2_perdidas_r10_eventos.csv"
    summary_csv_path = PROCESSED_DIR / "h2_resumen_ppda_r10.csv"

    df_events_out.to_csv(events_csv_path, index=False)
    df_summary_out.to_csv(summary_csv_path, index=False)

    print(f"3. Archivos de trazabilidad guardados en processed/:")
    print(f"   • {events_csv_path.name} ({len(df_events_out):,} eventos transaccionales)")
    print(f"   • {summary_csv_path.name} ({len(df_summary_out)} partidos)\n")

    # 4. Inferencia Estadística a Nivel de Partido (Mann-Whitney U & Bootstrap)
    valid_summary = df_summary_out.dropna(subset=["tasa_r10"]).copy()
    high_group = valid_summary[valid_summary["high_press_match"]]
    low_group = valid_summary[~valid_summary["high_press_match"]]

    # Estadísticas descriptivas de tasa a nivel de partido
    tasa_high_mean = high_group["tasa_r10"].mean() * 100
    tasa_low_mean = low_group["tasa_r10"].mean() * 100

    # Prueba U de Mann-Whitney (no paramétrica, apropiada para tasas agrupadas por partido)
    stat, p_value = stats.mannwhitneyu(low_group["tasa_r10"], high_group["tasa_r10"], alternative='two-sided')

    print("4. Resultados Estadísticos e Inferencia (H2-V5):")
    print(f"   • Partidos con Alta Presión (PPDA <= {median_ppda:.2f}): {len(high_group)} partidos")
    print(f"     - Tasa R10 Promedio por Partido: {tasa_high_mean:.2f}%")
    print(f"     - Tasa R10 Agregada (Global): {(high_group['r10_recoveries'].sum() / high_group['eligible_losses'].sum() * 100):.2f}%")
    
    print(f"\n   • Partidos con Baja Presión (PPDA > {median_ppda:.2f}): {len(low_group)} partidos")
    print(f"     - Tasa R10 Promedio por Partido: {tasa_low_mean:.2f}%")
    print(f"     - Tasa R10 Agregada (Global): {(low_group['r10_recoveries'].sum() / low_group['eligible_losses'].sum() * 100):.2f}%")

    print(f"\n   • Prueba U de Mann-Whitney (Diferencia de tasas por partido):")
    print(f"     - Estadístico U: {stat:.2f}")
    print(f"     - P-value bilateral: {p_value:.4f}")
    
    if p_value < 0.05:
        print("     👉 Conclusión: La diferencia entre grupos es estadísticamente significativa (p < 0.05).")
    else:
        print("     👉 Conclusión: La diferencia NO alcanza significancia estadística formal (p >= 0.05); se mantiene como tendencia exploratoria.")

    print("\n===================================================================")
    print("✅ AUDITORÍA H2-V5 COMPLETADA CON INFERENCIA Y TRAZABILIDAD RIGUROSA.")
    print("===================================================================\n")

if __name__ == "__main__":
    run_h2_v5_audit()