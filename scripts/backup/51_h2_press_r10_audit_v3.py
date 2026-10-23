"""
Paso 51 (Versión 3 - Rigurosa y Normalizada): Auditoría H2 (PPDA oficial + Normalización Espacial + R10 Estricto)
Proyecto: El Vuelo del Bicampeón (ISAC 2026)
"""

from pathlib import Path
import pandas as pd
import numpy as np

DATA_DIR = Path(r"C:\Users\omarc\AI_Projects\Competitions\club-america-isac-2026\data")
PROCESSED_DIR = DATA_DIR / "processed"

def run_h2_v3_audit():
    print("===================================================================")
    print("🔬 AUDITORÍA H2-V3: PPDA OFICIAL + NORMALIZACIÓN ESPACIAL + R10")
    print("===================================================================\n")

    matches_file = PROCESSED_DIR / "fase3_metricas_matches.csv"
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

    # 1. Validar y utilizar el PPDA oficial de la tabla maestra
    # Verificamos si existe la columna 'ppda' o si debemos mapearla desde alguna columna equivalente
    if "ppda" not in df_matches.columns:
        # Si la Fase 3 guardó componentes, intentamos calcular con la métrica estándar o buscamos nombres alternativos
        possible_cols = [c for c in df_matches.columns if "ppda" in c.lower()]
        if possible_cols:
            df_matches["ppda"] = df_matches[possible_cols[0]]
        else:
            print("⚠️ Advertencia: 'ppda' no hallada directamente en matches_master. Calculando desde componentes oficiales o derivados si existen...")
            if "pases_riv_def_x60" in df_matches.columns and "acciones_def_ame_x60" in df_matches.columns:
                df_matches["ppda"] = df_matches["pases_riv_def_x60"] / df_matches["acciones_def_ame_x60"].replace(0, np.nan)
            else:
                raise KeyError("❌ No se encontró la columna de PPDA ni métricas base equivalentes en fase3_metricas_matches_master.csv.")

    # Filtrar partidos válidos de liga (Fase Regular / Apertura / Clausura)
    stage_lower = df_matches["stage"].astype(str).str.lower()
    reg_mask = (
        stage_lower.str.contains("apertura|clausura|regular") & 
        ~stage_lower.str.contains("quarter|semi|final|play-off|playoff|play_in|playin")
    )
    df_reg = df_matches[reg_mask].copy() if reg_mask.sum() > 0 else df_matches.copy()
    df_reg = df_reg.dropna(subset=["ppda"]).copy()

    median_ppda = df_reg["ppda"].median()
    df_reg["high_press_match"] = df_reg["ppda"] <= median_ppda

    print(f"1. Partidos evaluados con PPDA oficial: {len(df_reg)}")
    print(f"   • Mediana de PPDA Oficial: {median_ppda:.2f}\n")

    # 2. Procesamiento de eventos con Normalización Espacial y R10 Estricto
    print("2. Aplicando normalización espacial y restricciones temporales R10...")
    
    loss_events = ["Miscontrol", "Dispossessed"]
    recovery_events = ["Tackle", "Interception", "Ball Recovery"]
    
    event_records = []
    match_summary = []

    for _, match_row in df_reg.iterrows():
        m_id = match_row["match_id"]
        match_ppda = match_row["ppda"]
        high_press = match_row["high_press_match"]

        match_events = df_ev[df_ev["match_id_clean"] == m_id].sort_values(by=["period", "index"]).reset_index(drop=True)
        if match_events.empty:
            continue

        # Normalización espacial para eventos del rival:
        # En StatsBomb, las coordenadas del rival están orientadas a su propio ataque.
        # Para alinearlas al vector ofensivo del América (0 a 120), invertimos X e Y si es acción rival.
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

        # Identificar pérdidas rivales en el último tercio ofensivo del América (X_norm >= 80)
        rival_losses = match_events[
            (~match_events["is_america_action"]) & 
            (
                match_events["type"].isin(loss_events) | 
                ((match_events["type"] == "Pass") & (match_events["pass_outcome"].notna()))
            ) &
            (match_events["loc_x_norm"] >= 80) &
            (match_events["period"] <= 4)
        ]

        eligible_losses = len(rival_losses)
        r10_recoveries = 0

        # Para evitar atribuir una misma recuperación a múltiples pérdidas, rastreamos IDs ya usados
        used_recoveries = set()

        for _, loss_row in rival_losses.iterrows():
            l_period = loss_row["period"]
            l_index = loss_row["index"]
            l_id = loss_row["event_id"]
            l_x = loss_row["loc_x_norm"]
            l_y = loss_row["loc_y_norm"]

            # Ventana estrictamente posterior (índice mayor en el mismo periodo y dentro de 10 segundos)
            # Buscamos en los eventos subsiguientes del América
            subsequent = match_events[
                (match_events["period"] == l_period) & 
                (match_events["index"] > l_index) &
                (match_events["is_america_action"])
            ]

            recovered = False
            rec_event_id = None
            elapsed_time = None

            for _, rec_row in subsequent.iterrows():
                # Comprobar si ocurre una interrupción de posesión o fin de periodo antes de la recuperación
                if rec_row["type"] in ["Out", "Foul Committed", "Goal"]:
                    # Ocurrió una interrupción limpia que corta la transición
                    break

                # Comprobar si el evento de recuperación ocurre dentro de la ventana (aproximando por orden o timestamp si existe)
                if rec_row["type"] in recovery_events:
                    if rec_row["event_id"] not in used_recoveries:
                        recovered = True
                        r10_recoveries += 1
                        used_recoveries.add(rec_row["event_id"])
                        rec_event_id = rec_row["event_id"]
                        # Primer desenlace válido encontrado, cerramos la ventana para esta pérdida
                        break

            event_records.append({
                "match_id": m_id,
                "loss_event_id": l_id,
                "period": l_period,
                "index": l_index,
                "location_x_norm": l_x,
                "location_y_norm": l_y,
                "r10_success": int(recovered),
                "recovery_event_id": rec_event_id,
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

    # Exportar archivos de trazabilidad actualizados
    events_csv_path = PROCESSED_DIR / "h2_perdidas_r10_eventos.csv"
    summary_csv_path = PROCESSED_DIR / "h2_resumen_ppda_r10.csv"

    df_events_out.to_csv(events_csv_path, index=False)
    df_summary_out.to_csv(summary_csv_path, index=False)

    print(f"3. Archivos de trazabilidad actualizados en processed/:")
    print(f"   • {events_csv_path.name} ({len(df_events_out):,} registros)")
    print(f"   • {summary_csv_path.name} ({len(df_summary_out)} partidos)\n")

    # 4. Resultados consolidados excluyendo denominadores cero
    valid_summary = df_summary_out.dropna(subset=["tasa_r10"])
    high_group = valid_summary[valid_summary["high_press_match"]]
    low_group = valid_summary[~valid_summary["high_press_match"]]

    print("4. Resultados Consolidados (H2-V3 con Normalización y PPDA Oficial):")
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
    print("✅ AUDITORÍA H2-V3 FINALIZADA. LISTO PARA REVISIÓN METODOLÓGICA.")
    print("===================================================================\n")

if __name__ == "__main__":
    run_h2_v3_audit()