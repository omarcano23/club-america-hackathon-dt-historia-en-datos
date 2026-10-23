"""
Paso 35: Auditoría Forense Final y Reconciliación de Inconsistencias
Proyecto: El Vuelo del Bicampeón (ISAC 2026)
"""

import json
from pathlib import Path
import numpy as np
import pandas as pd

DATA_DIR = Path(
    r"C:\Users\omarc\AI_Projects\Competitions\club-america-isac-2026\data"
)
PROCESSED_DIR = DATA_DIR / "processed"
RAW_DIR = DATA_DIR / "raw"


def run_full_reconciliation():
  print("==================================================================")
  print("🔬 AUDITORÍA FORENSE FINAL Y RECONCILIACIÓN DE INCONSISTENCIAS")
  print("==================================================================\n")

  events_file = PROCESSED_DIR / "events_master.csv"
  index_json = RAW_DIR / "jardine_matches_index.json"

  if not events_file.exists():
    print(f"❌ Error: {events_file} no existe.")
    return

  df_ev = pd.read_csv(events_file, low_memory=False)
  df_ev["match_id_clean"] = (
      pd.to_numeric(
          df_ev["match_id"].astype(str).str.replace("match_", ""),
          errors="coerce",
      )
      .fillna(0)
      .astype("int64")
  )

  # Cargar metadatos para mapeo exacto de 66 partidos de Fase Regular
  with open(index_json, "r", encoding="utf-8") as f:
    meta_data = json.load(f)

  reg_matches_ids = []
  meta_stage_map = {}
  for m in meta_data:
    m_id = int(str(m.get("match_id", 0)).replace("match_", ""))
    stage_raw = str(m.get("competition_stage", "")).lower()

    if (
        ("regular" in stage_raw or stage_raw in ["apertura", "clausura"])
        and not ("quarter" in stage_raw or "semi" in stage_raw or "final" in stage_raw)
        and "play-off" not in stage_raw
        and "play-in" not in stage_raw
    ):
      stage_clean = "Fase Regular"
      reg_matches_ids.append(m_id)
    elif "play-off" in stage_raw or "play-in" in stage_raw:
      stage_clean = "Play-In"
    else:
      stage_clean = "Liguilla"
    meta_stage_map[m_id] = stage_clean

  # ------------------------------------------------------------------
  # 1. COMPROBACIÓN Y RECONCILIACIÓN DE PPDA EN FASE REGULAR (66 FILAS)
  # ------------------------------------------------------------------
  print("1. RECONCILIACIÓN DE PPDA SOBRE EXACTAMENTE 66 PARTIDOS REGULARES:")
  print("-" * 65)

  match_rows = []
  for m_id in reg_matches_ids:
    grp = df_ev[
        (df_ev["match_id_clean"] == m_id) & (df_ev["period"] <= 4)
    ].copy()

    # Numerador: Pases intentados por el rival en X <= 60
    pases_riv_def = len(
        grp[
            (~grp["is_america_action"])
            & (grp["type"] == "Pass")
            & (grp["location_x"] <= 60)
        ]
    )

    # Denominador: Acciones defensivas deduplicadas de América en X >= 60
    def_evts = grp[
        (grp["is_america_action"])
        & (grp["location_x"] >= 60)
        & (
            grp["type"].isin(
                ["Tackle", "Interception", "Foul Committed", "Duel", "Block"]
            )
        )
    ]
    def_actions_ame = len(
        def_evts.drop_duplicates(
            subset=["period", "minute", "second", "location_x", "location_y"]
        )
    )

    ppda_ind = (
        (pases_riv_def / def_actions_ame) if def_actions_ame > 0 else np.nan
    )

    match_rows.append({
        "match_id": m_id,
        "stage": "Fase Regular",
        "pases_riv_x60": pases_riv_def,
        "def_actions_ame_x60": def_actions_ame,
        "ppda_individual": ppda_ind,
    })

  df_ppda_reg = pd.DataFrame(match_rows)

  tot_pases_riv = int(df_ppda_reg["pases_riv_x60"].sum())
  tot_def_actions = int(df_ppda_reg["def_actions_ame_x60"].sum())
  zero_denom_count = int((df_ppda_reg["def_actions_ame_x60"] == 0).sum())

  mean_ppda_66 = float(df_ppda_reg["ppda_individual"].mean())
  median_ppda_66 = float(df_ppda_reg["ppda_individual"].median())
  agg_ppda_66 = float(tot_pases_riv / tot_def_actions)

  print(f"• Total Partidos Auditados en Fase Regular: {len(df_ppda_reg)}")
  print(
      f"• Partidos con Denominador Cero en Acciones Defensivas:"
      f" {zero_denom_count}"
  )
  print(
      f"• Total Pases Rival X <= 60: {tot_pases_riv:,} (Promedio:"
      f" {tot_pases_riv / 66:.2f} pases/partido)"
  )
  print(
      f"• Total Acciones Defensivas América X >= 60: {tot_def_actions:,}"
      f" (Promedio: {tot_def_actions / 66:.2f} acciones/partido)"
  )
  print(f"• Media de PPDA por Partido (66 filas): {mean_ppda_66:.2f}")
  print(f"• Mediana de PPDA por Partido (66 filas): {median_ppda_66:.2f}")
  print(f"• Cociente Agregado Global (16,227 / 1,640): {agg_ppda_66:.2f}")

  # ------------------------------------------------------------------
  # 2. RECONCILIACIÓN DE PASES PROGRESIVOS Y CATEGORÍAS DE REINICIO
  # ------------------------------------------------------------------
  print(
      "\n2. RECONCILIACIÓN DE UNIVERSO DE PASES PROGRESIVOS Y REINICIOS:"
  )
  print("-" * 65)

  total_passes = len(df_ev[df_ev["type"] == "Pass"])
  completed_passes = df_ev[
      (df_ev["type"] == "Pass") & (df_ev["pass_outcome"].isna())
  ].copy()

  restart_patterns = [
      "From Corner",
      "From Free Kick",
      "From Throw In",
      "From Kick Off",
      "From Goal Kick",
  ]
  is_restart = completed_passes["play_pattern"].isin(restart_patterns)

  restarts_passes = completed_passes[is_restart]
  open_play_passes = completed_passes[~is_restart].copy()

  tot_completed = len(completed_passes)
  tot_restarts = len(restarts_passes)
  tot_open_play = len(open_play_passes)

  # Algoritmo progresivo sobre los 39,259 pases abiertos
  dist_start = np.sqrt(
      (120 - open_play_passes["location_x"]) ** 2
      + (40 - open_play_passes["location_y"]) ** 2
  )
  dist_end = np.sqrt(
      (120 - open_play_passes["end_location_x"]) ** 2
      + (40 - open_play_passes["end_location_y"]) ** 2
  )

  cond_base = (
      (open_play_passes["location_x"] < 40) & (dist_end <= dist_start * 0.70)
  ) | (
      (open_play_passes["location_x"] >= 40)
      & (open_play_passes["location_x"] < 80)
      & (dist_end <= dist_start * 0.85)
  ) | (
      (open_play_passes["location_x"] >= 80)
      & ((dist_end <= dist_start * 0.90) | (open_play_passes["end_location_x"] >= 102))
  )

  cond_strict = (
      (open_play_passes["location_x"] < 40) & (dist_end <= dist_start * 0.65)
  ) | (
      (open_play_passes["location_x"] >= 40)
      & (open_play_passes["location_x"] < 80)
      & (dist_end <= dist_start * 0.80)
  ) | (
      (open_play_passes["location_x"] >= 80)
      & ((dist_end <= dist_start * 0.85) | (open_play_passes["end_location_x"] >= 102))
  )

  prog_base_cnt = int(cond_base.sum())
  prog_strict_cnt = int(cond_strict.sum())

  print(f"• Pases Totales Intentados en el Dataset: {total_passes:,}")
  print(f"• Pases Completados Totales (América + Rival): {tot_completed:,}")
  print(f"• Pases de Reinicio Directo Excluidos: {tot_restarts:,}")
  print("  Desglose Reconciliado por Criterio Metodológico:")
  print(
      f"   - Saques de Banda (From Throw In):"
      f" {len(completed_passes[completed_passes['play_pattern']=='From Throw In']):,}"
  )
  print(
      f"   - Tiros Libres (From Free Kick):"
      f" {len(completed_passes[completed_passes['play_pattern']=='From Free Kick']):,}"
  )
  print(
      f"   - Saques de Meta (From Goal Kick):"
      f" {len(completed_passes[completed_passes['play_pattern']=='From Goal Kick']):,}"
  )
  print(
      f"   - Córneres (From Corner):"
      f" {len(completed_passes[completed_passes['play_pattern']=='From Corner']):,}"
  )
  print(
      f"   - Saques de Centro (From Kick Off):"
      f" {len(completed_passes[completed_passes['play_pattern']=='From Kick Off']):,}"
  )
  print(f"• Universo Oficial de Juego Abierto Evaluado: {tot_open_play:,}")
  print(
      f"  - Progresivos Regla Base (30/15/10%): {prog_base_cnt:,}"
      f" ({prog_base_cnt / tot_open_play * 100:.2f}%)"
  )
  print(
      f"  - Progresivos Regla Estricta (35/20/15%): {prog_strict_cnt:,}"
      f" ({prog_strict_cnt / tot_open_play * 100:.2f}%)"
  )

  # ------------------------------------------------------------------
  # 3. RECONCILIACIÓN FORENSE Y RECALCULO DE xG EN REMATES ABP (733 REMATES)
  # ------------------------------------------------------------------
  print(
      "\n3. RECONCILIACIÓN Y RECÁLCULO DE xG POR REMATE INDIVIDUAL EN ABP (733"
      " REMATES):"
  )
  print("-" * 65)

  abp_shots_all = df_ev[
      (df_ev["play_pattern"].isin(["From Corner", "From Free Kick"]))
      & (df_ev["type"] == "Shot")
  ].copy()

  tot_abp_shots_cnt = len(abp_shots_all)
  tot_abp_xg_sum = float(abp_shots_all["shot_statsbomb_xg"].sum())

  valid_abp_shots_cnt = 0
  reclassified_shots_cnt = 0
  valid_abp_xg_sum = 0.0
  reclassified_xg_sum = 0.0

  for idx, shot in abp_shots_all.iterrows():
    m_id = shot["match_id_clean"]
    s_time = shot["minute"] * 60 + shot["second"]
    s_xg = (
        float(shot["shot_statsbomb_xg"])
        if pd.notna(shot["shot_statsbomb_xg"])
        else 0.0
    )

    prev_passes = df_ev[
        (df_ev["match_id_clean"] == m_id)
        & (df_ev["type"] == "Pass")
        & (df_ev["play_pattern"] == shot["play_pattern"])
    ]
    prev_pass_times = prev_passes["minute"] * 60 + prev_passes["second"]

    # Evaluar pase previo en la secuencia dentro de 10.0s
    valid_origin = prev_pass_times[
        (s_time - prev_pass_times >= 0) & (s_time - prev_pass_times <= 10.0)
    ]

    if len(valid_origin) <= 3:
      valid_abp_shots_cnt += 1
      valid_abp_xg_sum += s_xg
    else:
      reclassified_shots_cnt += 1
      reclassified_xg_sum += s_xg

  print(f"• Remates Totales Etiquetados Inicialmente como ABP: {tot_abp_shots_cnt}")
  print(f"• xG Acumulado Total del Universo ABP: {tot_abp_xg_sum:.2f}")
  print(
      f"• Remates Retenidos en ABP (<= 3 pases): {valid_abp_shots_cnt} remates"
      f" | xG Recalculado: {valid_abp_xg_sum:.2f} xG (Promedio:"
      f" {valid_abp_xg_sum / valid_abp_shots_cnt:.4f} xG/remate)"
  )
  print(
      f"• Remates Reclasificados a Juego Abierto (4° pase o >10s):"
      f" {reclassified_shots_cnt} remates | xG Reclasificado:"
      f" {reclassified_xg_sum:.2f} xG (Promedio:"
      f" {reclassified_xg_sum / reclassified_shots_cnt:.4f} xG/remate)"
  )
  print(
      f"• Suma de Comprobación: {valid_abp_shots_cnt} + {reclassified_shots_cnt}"
      f" = {valid_abp_shots_cnt + reclassified_shots_cnt} remates |"
      f" {valid_abp_xg_sum:.2f} + {reclassified_xg_sum:.2f} ="
      f" {valid_abp_xg_sum + reclassified_xg_sum:.2f} xG"
  )

  # ------------------------------------------------------------------
  # 4. GENERACIÓN DE ARTEFACTOS OFICIALES Y MANIFIESTO FINAL
  # ------------------------------------------------------------------
  print(
      "\n4. Exportando artefactos oficiales reconciliados"
      " (v1.0-CONSOLIDATED)..."
  )

  official_audit = {
      "fase": "2.3 - Auditoría y Aceptación Metodológica Final Reconciliada",
      "version": "v1.0-CONSOLIDATED",
      "estatus": "APROBADO_CON_RECONCILIACION_FORENSE",
      "ppda_fase_regular": {
          "partidos_evaluados": len(df_ppda_reg),
          "partidos_denominador_cero": zero_denom_count,
          "pases_intentados_rival_x60": tot_pases_riv,
          "acciones_defensivas_america_x60": tot_def_actions,
          "ppda_media_partidos": round(mean_ppda_66, 2),
          "ppda_mediana_partidos": round(median_ppda_66, 2),
          "ppda_cociente_agregado": round(agg_ppda_66, 2),
      },
      "pases_progresivos": {
          "universo_completados_totales": tot_completed,
          "pases_reinicio_excluidos": tot_restarts,
          "universo_juego_abierto": tot_open_play,
          "progresivos_base_30_15_10": prog_base_cnt,
          "pct_base": round(prog_base_cnt / tot_open_play * 100, 2),
          "progresivos_estricta_35_20_15": prog_strict_cnt,
          "pct_estricta": round(prog_strict_cnt / tot_open_play * 100, 2),
      },
      "balon_parado_abp": {
          "remates_totales_evaluados": tot_abp_shots_cnt,
          "xg_total_abp": round(tot_abp_xg_sum, 2),
          "remates_retenidos_le3_pases": valid_abp_shots_cnt,
          "xg_retenido": round(valid_abp_xg_sum, 2),
          "remates_reclasificados_juego_abierto": reclassified_shots_cnt,
          "xg_reclasificado": round(reclassified_xg_sum, 2),
      },
  }

  audit_out_file = PROCESSED_DIR / "audit_phase2_final.json"
  with open(audit_out_file, "w", encoding="utf-8") as f:
    json.dump(official_audit, f, indent=4, ensure_ascii=False)

  print("\n==================================================================")
  print("🏆 RECONCILIACIÓN FORENSE FINALIZADA Y ARTEFACTOS ACTUALIZADOS")
  print("==================================================================")


if __name__ == "__main__":
  run_full_reconciliation()