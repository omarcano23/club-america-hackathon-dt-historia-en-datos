"""
Paso 60 (Fases B y C Corregidas): Corrección Espacial de Presión Alta (X <= 40)
y Motor Definitivo de Máquina de Estados R10.
Proyecto: El Vuelo del Bicampeón (ISAC 2026)
"""

from pathlib import Path
import pandas as pd
import numpy as np
from scipy import stats

DATA_DIR = Path(r"C:\Users\omarc\AI_Projects\Competitions\club-america-isac-2026\data")
PROCESSED_DIR = DATA_DIR / "processed"

def run_corrected_h2():
    print("===================================================================")
    print("🔬 FASES B & C CORREGIDAS: PRESIÓN ALTA EN SALIDA RIVAL (X <= 40)")
    print("==================================================================-\n")

    matches_file = PROCESSED_DIR / "fase3_matches_master_unificado.csv"
    events_file = PROCESSED_DIR / "events_master.csv"

    if not matches_file.exists() or not events_file.exists():
        print(matches_file)
        print(events_file)
        print("❌ Error: Faltan archivos maestros en processed/.")
        return

    df_matches = pd.read_csv(matches_file)
    df_ev = pd.read_csv(events_file, low_memory=False)
    
    df_ev["match_id_clean"] = pd.to_numeric(
        df_ev["match_id"].astype(str).str.replace("match_", ""),
        errors="coerce"
    ).fillna(-1).astype("int64")

    if "ppda" not in df_matches.columns:
        raise KeyError("❌ La columna 'ppda' no se encuentra en la tabla maestra.")

    # Filtro estricto de Fase Regular
    stage_lower = df_matches["stage"].astype(str).str.lower()
    reg_mask = (
        stage_lower.str.contains("apertura|clausura|regular") & 
        ~stage_lower.str.contains("quarter|semi|final|play-off|playoff|play_in|playin")
    )
    df_reg = df_matches[reg_mask].copy() if reg_mask.sum() > 0 else None
    
    if df_reg is None or len(df_reg) == 0:
        raise ValueError("❌ Error crítico: El filtro de Fase Regular no devolvió partidos.")

    df_reg = df_reg.dropna(subset=["ppda"]).copy()
    median_ppda = df_reg["ppda"].median()
    df_reg["high_press_match"] = df_reg["ppda"] <= median_ppda

    print(f"1. Partidos de Fase Regular validados: {len(df_reg)}")
    print(f"   • Mediana de PPDA Oficial: {median_ppda:.2f}\n")

    print("2. Aplicando filtro espacial corregido (X <= 40: Tercio Defensivo / Salida Rival)...")
    
    strict_restarts = ["From Corner", "From Free Kick", "From Goal Kick", "From Kick Off", "From Throw In"]
    valid_pass_outcomes = ["Incomplete"]
    recovery_types = ["Interception", "Ball Recovery"]
    interruption_types = ["Foul Committed", "Out"]

    transition_records = []
    match_summary = []

    for _, match_row in df_reg.iterrows():
        m_id = match_row["match_id"]
        match_ppda = match_row["ppda"]
        high_press = match_row["high_press_match"]

        match_events = df_ev[df_ev["match_id_clean"] == m_id].sort_values(by=["period", "index"]).reset_index(drop=True)
        if match_events.empty:
            continue

        match_events["period_seconds"] = match_events["minute"] * 60 + match_events["second"]

        # Definición corregida de pérdida elegible en salida rival (X <= 40, juego abierto)
        def is_valid_loss_corrected(row):
            if row["is_america_action"]:
                return False
            if row["period"] > 4:
                return False
            # CORRECCIÓN ESPACIAL: Tercio defensivo del rival (X <= 40) donde América ejerce presión alta
            if row["location_x"] > 40:
                return False
            if row["play_pattern"] in strict_restarts:
                return False
            
            t = row["type"]
            po = row["pass_outcome"]
            
            if t in ["Miscontrol", "Dispossessed"]:
                return True
            if t == "Pass":
                if pd.isna(po):
                    return False
                return str(po).strip() in valid_pass_outcomes
            return False

        match_events["is_valid_loss"] = match_events.apply(is_valid_loss_corrected, axis=1)
        rival_losses = match_events[match_events["is_valid_loss"]].copy()

        eligible_losses = 0
        r10_recoveries = 0
        used_recoveries = set()

        events_list = match_events.to_dict(orient="records")
        losses_list = rival_losses.to_dict(orient="records")

        for i, loss in enumerate(losses_list):
            eligible_losses += 1
            l_id = loss["event_id"]
            l_period = loss["period"]
            l_index = loss["index"]
            l_time = loss["period_seconds"]

            next_loss_index = float('inf')
            if i + 1 < len(losses_list):
                if losses_list[i+1]["period"] == l_period:
                    next_loss_index = losses_list[i+1]["index"]

            terminal_outcome = "VENTANA_AGOTADA"
            rec_event_id = None
            elapsed_time = None
            recovered = False

            for ev in events_list:
                if ev["period"] != l_period or ev["index"] <= l_index:
                    continue

                sub_time = ev["period_seconds"]
                delta_t = sub_time - l_time

                if delta_t > 10.0:
                    terminal_outcome = "VENTANA_AGOTADA"
                    break

                if delta_t <= 0:
                    continue

                if ev["index"] >= next_loss_index:
                    terminal_outcome = "NUEVA_PERDIDA_RIVAL"
                    break

                if not ev["is_america_action"]:
                    pass_outcome = ev.get("pass_outcome", np.nan)
                    is_pass_success = (ev["type"] == "Pass") and (pd.isna(pass_outcome) or str(pass_outcome).strip() == "")
                    
                    if is_pass_success:
                        terminal_outcome = "SALIDA_RIVAL_CONFIRMADA"
                        break
                    if ev["type"] in interruption_types:
                        terminal_outcome = "INTERRUPCION"
                        break
                    if ev["type"] == "Shot":
                        terminal_outcome = "REMATE_RIVAL"
                        break

                if ev["is_america_action"] and ev["type"] in recovery_types:
                    if ev["event_id"] not in used_recoveries:
                        recovered = True
                        r10_recoveries += 1
                        used_recoveries.add(ev["event_id"])
                        rec_event_id = ev["event_id"]
                        elapsed_time = delta_t
                        terminal_outcome = "RECUPERACION_EFECTIVA"
                        break

            transition_records.append({
                "match_id": m_id,
                "loss_event_id": l_id,
                "recovery_event_id": rec_event_id,
                "elapsed_seconds": elapsed_time,
                "r10_success": int(recovered),
                "terminal_outcome": terminal_outcome,
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

    df_trans_out = pd.DataFrame(transition_records)
    df_summary_out = pd.DataFrame(match_summary)

    # Exportar resultados corregidos
    trans_csv_path = PROCESSED_DIR / "h2_corregido_transacciones.csv"
    summary_csv_path = PROCESSED_DIR / "h2_corregido_resumen_partido.csv"
    df_trans_out.to_csv(trans_csv_path, index=False)
    df_summary_out.to_csv(summary_csv_path, index=False)

    print(f"3. Archivos corregidos guardados en processed/:")
    print(f"   • {trans_csv_path.name} ({len(df_trans_out):,} transacciones)")
    print(f"   • {summary_csv_path.name} ({len(df_summary_out)} partidos)\n")

    # 4. Inferencia Estadística Corregida (Mann-Whitney U & Bootstrap 95%)
    valid_summary = df_summary_out.dropna(subset=["tasa_r10"]).copy()
    high_group = valid_summary[valid_summary["high_press_match"]]["tasa_r10"].values * 100
    low_group = valid_summary[~valid_summary["high_press_match"]]["tasa_r10"].values * 100

    mean_high = np.mean(high_group)
    mean_low = np.mean(low_group)
    median_high = np.median(high_group)
    median_low = np.median(low_group)
    diff_means = mean_high - mean_low

    stat, p_value = stats.mannwhitneyu(low_group, high_group, alternative='two-sided')

    np.random.seed(42)
    n_boot = 10000
    boot_diffs = []
    for _ in range(n_boot):
        boot_high = np.random.choice(high_group, size=len(high_group), replace=True)
        boot_low = np.random.choice(low_group, size=len(low_group), replace=True)
        boot_diffs.append(np.mean(boot_high) - np.mean(boot_low))
    
    ci_lower = np.percentile(boot_diffs, 2.5)
    ci_upper = np.percentile(boot_diffs, 97.5)

    print("4. Resultados Estadísticos Corregidos (Presión en Salida Rival X <= 40):")
    print(f"   • Alta Presión (PPDA <= {median_ppda:.2f}): Tasa Media = {mean_high:.2f}% (Mediana: {median_high:.2f}%, n={len(high_group)})")
    print(f"   • Baja Presión (PPDA > {median_ppda:.2f}): Tasa Media = {mean_low:.2f}% (Mediana: {median_low:.2f}%, n={len(low_group)})")
    print(f"   • Diferencia de Medias (Alta - Baja): {diff_means:+.2f} pp")
    print(f"   • Intervalo de Confianza Bootstrap 95%: [{ci_lower:+.2f} pp, {ci_upper:+.2f} pp]")
    print(f"   • Prueba U de Mann-Whitney: p-value = {p_value:.4f}")
    
    print("\n   📊 Desglose Terminal de Transacciones:")
    print(df_trans_out["terminal_outcome"].value_counts().to_string())

    print("\n===================================================================")
    print("✅ FASES B & C CORREGIDAS EXITOSAMENTE.")
    print("==================================================================-\n")

if __name__ == "__main__":
    run_corrected_h2()