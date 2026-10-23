"""
Paso 57 (Fase C - Auditoría R10 y Máquina de Estados Definitiva):
Ejecución de la hipótesis H2 sobre el denominador congelado de 1,125 pérdidas.
Proyecto: El Vuelo del Bicampeón (ISAC 2026)
"""

from pathlib import Path
import pandas as pd
import numpy as np
from scipy import stats

DATA_DIR = Path(r"C:\Users\omarc\AI_Projects\Competitions\club-america-isac-2026\data")
PROCESSED_DIR = DATA_DIR / "processed"

def run_fase_c_r10_audit():
    print("===================================================================")
    print("🔬 FASE C: AUDITORÍA TEMPORAL R10 Y MÁQUINA DE ESTADOS ESTRICTA")
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

    print("2. Ejecutando máquina de estados temporal R10 sobre el denominador congelado...")
    
    strict_restarts = ["From Corner", "From Free Kick", "From Goal Kick", "From Kick Off", "From Throw In"]
    valid_pass_outcomes = ["Incomplete", "Out", "Pass Offside"]
    recovery_types = ["Interception", "Ball Recovery"]
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

        match_events["period_seconds"] = match_events["minute"] * 60 + match_events["second"]

        # Aplicar el denominador congelado de la Fase B
        def is_valid_loss(row):
            if row["is_america_action"]:
                return False
            if row["period"] > 4:
                return False
            if row["location_x"] < 80:
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

        match_events["is_valid_loss"] = match_events.apply(is_valid_loss, axis=1)
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
            l_x = loss["location_x"]
            l_y = loss["location_y"]

            next_loss_index = float('inf')
            if i + 1 < len(losses_list):
                if losses_list[i+1]["period"] == l_period:
                    next_loss_index = losses_list[i+1]["index"]

            recovered = False
            rec_event_id = None
            elapsed_time = None
            outcome = "sin_recuperacion_en_ventana"
            exclusion_reason = None

            for ev in events_list:
                if ev["period"] != l_period or ev["index"] <= l_index:
                    continue

                sub_time = ev["period_seconds"]
                delta_t = sub_time - l_time

                # 1. Límite estricto de 10 segundos
                if delta_t > 10.0:
                    exclusion_reason = "fuera_de_ventana_10s"
                    break

                # 2. Descartar simultaneidades (delta_t <= 0)
                if delta_t <= 0:
                    continue

                # 3. Cierre por nueva pérdida rival
                if ev["index"] >= next_loss_index:
                    exclusion_reason = "interrumpido_por_nueva_perdida_rival"
                    break

                # 4. Control bilateral de interrupciones o salidas rivales
                if not ev["is_america_action"]:
                    pass_outcome = ev.get("pass_outcome", np.nan)
                    is_pass_success = (ev["type"] == "Pass") and (pd.isna(pass_outcome) or str(pass_outcome).strip() == "")
                    
                    if is_pass_success:
                        exclusion_reason = "salida_exitosa_rival"
                        break
                    if ev["type"] in interruption_types:
                        exclusion_reason = "interrupcion_juego"
                        break

                # 5. Recuperación efectiva del América
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
                "location_x": l_x,
                "location_y": l_y,
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

    # Exportar trazabilidad de Fase C
    events_csv_path = PROCESSED_DIR / "h2_fase_c_perdidas_r10_eventos.csv"
    summary_csv_path = PROCESSED_DIR / "h2_fase_c_resumen_ppda_r10.csv"
    df_events_out.to_csv(events_csv_path, index=False)
    df_summary_out.to_csv(summary_csv_path, index=False)

    print(f"3. Archivos de trazabilidad de Fase C guardados en processed/:")
    print(f"   • {events_csv_path.name} ({len(df_events_out):,} eventos)")
    print(f"   • {summary_csv_path.name} ({len(df_summary_out)} partidos)\n")

    # 4. Inferencia Estadística Definitiva: Mann-Whitney U y Bootstrap 95%
    valid_summary = df_summary_out.dropna(subset=["tasa_r10"]).copy()
    high_group = valid_summary[valid_summary["high_press_match"]]["tasa_r10"].values * 100
    low_group = valid_summary[~valid_summary["high_press_match"]]["tasa_r10"].values * 100

    mean_high = np.mean(high_group)
    mean_low = np.mean(low_group)
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

    print("4. Resultados Estadísticos Definitivos sobre Denominador Validado (Fase C):")
    print(f"   • Alta Presión (PPDA <= {median_ppda:.2f}): Tasa Media por Partido = {mean_high:.2f}% (n={len(high_group)})")
    print(f"   • Baja Presión (PPDA > {median_ppda:.2f}): Tasa Media por Partido = {mean_low:.2f}% (n={len(low_group)})")
    print(f"   • Diferencia de Medias (Alta - Baja): {diff_means:+.2f} pp")
    print(f"   • Intervalo de Confianza Bootstrap 95%: [{ci_lower:+.2f} pp, {ci_upper:+.2f} pp]")
    print(f"   • Prueba U de Mann-Whitney: p-value = {p_value:.4f}")
    
    if p_value < 0.05:
        print("     👉 Conclusión: Diferencia estadísticamente significativa (p < 0.05).")
    else:
        print("     👉 Conclusión: La diferencia NO alcanza significancia formal (p >= 0.05). Clasificación: Exploratoria robusta.")

    print("\n===================================================================")
    print("✅ FASE C COMPLETADA EXITOSAMENTE. H2 AUDITADA Y TRAZADA.")
    print("===================================================================\n")

if __name__ == "__main__":
    run_fase_c_r10_audit()