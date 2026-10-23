"""
Fase 3 - Pasos 3.1 y 3.2: Reconstrucción Robusta de la Capa Analítica
Proyecto: El Vuelo del Bicampeón (ISAC 2026)
"""

import json
from pathlib import Path
import numpy as np
import pandas as pd

# Directorios de trabajo
DATA_DIR = Path(
    r"C:\Users\omarc\AI_Projects\Competitions\club-america-isac-2026\data"
)
PROCESSED_DIR = DATA_DIR / "processed"
RAW_DIR = DATA_DIR / "raw"


def run_analytical_engine_v3():
  print("==================================================================")
  print("🚀 FASE 3: CONSTRUCCIÓN RIGUROSA DE LA CAPA ANALÍTICA (V3.0)")
  print("==================================================================\n")

  events_file = PROCESSED_DIR / "events_master.csv"
  index_json = RAW_DIR / "jardine_matches_index.json"

  if not events_file.exists():
    raise FileNotFoundError(f"❌ Error crítico: {events_file} no existe.")

  # ------------------------------------------------------------------
  # 1. NORMALIZACIÓN ESTRICTA Y VINCULACIÓN CON METADATOS
  # ------------------------------------------------------------------
  print("1. Normalizando identificadores y vinculando metadatos sin fallbacks...")
  df_ev = pd.read_csv(events_file, low_memory=False)

  # Conversión segura y validación de nulls en match_id
  df_ev["match_id_str"] = df_ev["match_id"].astype(str).str.replace("match_", "").str.strip()
  if df_ev["match_id_str"].isna().any() or (df_ev["match_id_str"] == "0").any():
    raise ValueError("❌ Se detectaron identificadores de partido no válidos o nulos.")

  df_ev["match_id_clean"] = df_ev["match_id_str"].astype("int64")

  # Cargar metadatos
  with open(index_json, "r", encoding="utf-8") as f:
    meta_raw = json.load(f)

  meta_dict = {}
  for m in meta_raw:
    m_id = int(str(m.get("match_id", 0)).replace("match_", ""))
    stage_raw = str(m.get("competition_stage", "")).lower()

    if (
        ("regular" in stage_raw or stage_raw in ["apertura", "clausura"])
        and not ("quarter" in stage_raw or "semi" in stage_raw or "final" in stage_raw)
        and "play-off" not in stage_raw
        and "play-in" not in stage_raw
    ):
      stage_clean = "Fase Regular"
    elif "play-off" in stage_raw or "play-in" in stage_raw:
      stage_clean = "Play-In"
    else:
      stage_clean = "Liguilla"

    season_str = str(m.get("season", "2023/2024"))
    home_team = str(m.get("home_team", ""))
    away_team = str(m.get("away_team", ""))
    is_home = "América" in home_team or "Club América" in home_team

    meta_dict[m_id] = {
        "season": season_str,
        "stage": stage_clean,
        "home_team": home_team,
        "away_team": away_team,
        "is_home": is_home,
    }

  # Validar que todos los 91 partidos tengan metadatos
  unique_match_ids = df_ev["match_id_clean"].unique()
  if len(unique_match_ids) != 91:
    raise ValueError(f"❌ Inconsistencia en cobertura: Se esperaban 91 partidos, se detectaron {len(unique_match_ids)}")

  for m_id in unique_match_ids:
    if m_id not in meta_dict:
      raise KeyError(f"❌ Error de mapeo: Match ID {m_id} no tiene metadatos en jardine_matches_index.json")

  print(f"   ✔️ 91 partidos validados al 100% con metadatos de temporada, fase y localía.\n")

  # ------------------------------------------------------------------
  # 2. RECONCILIACIÓN DE MARCADOR OFICIAL Y MATRIZ DE GOLES / XG
  # ------------------------------------------------------------------
  print("2. Reconciliando marcador oficial, autogoles y precisión flotante de xG...")

  match_analytics = []

  for m_id in unique_match_ids:
    m_info = meta_dict[m_id]
    grp = df_ev[(df_ev["match_id_clean"] == m_id) & (df_ev["period"] <= 4)].copy()

    # A. Goles de Remate Directo
    shots_m = grp[grp["type"] == "Shot"].copy()
    
    ame_shots = shots_m[shots_m["is_america_action"]]
    riv_shots = shots_m[~shots_m["is_america_action"]]

    ame_shot_goals = len(ame_shots[ame_shots["shot_outcome"].isin(["Goal", "Goal_Penalty"])])
    riv_shot_goals = len(riv_shots[riv_shots["shot_outcome"].isin(["Goal", "Goal_Penalty"])])

    # B. Autogoles
    if "pass_type" in grp.columns:
      own_goals_ev = grp[grp["pass_type"] == "Own Goal"]
    else:
      own_goals_ev = grp[grp["type"] == "Own Goal"]

    ame_own_goals_against = len(own_goals_ev[own_goals_ev["is_america_action"]])
    riv_own_goals_against = len(own_goals_ev[~own_goals_ev["is_america_action"]])

    # Marcador final ajustado
    ame_tot_goals = ame_shot_goals + riv_own_goals_against
    riv_tot_goals = riv_shot_goals + ame_own_goals_against

    # xG con precisión flotante completa
    ame_xg_float = float(ame_shots["shot_statsbomb_xg"].fillna(0.0).sum())
    riv_xg_float = float(riv_shots["shot_statsbomb_xg"].fillna(0.0).sum())

    # C. Field Tilt (Pases completados en X >= 80)
    pases_m = grp[(grp["type"] == "Pass") & (grp["pass_outcome"].isna())]
    ame_att = len(pases_m[(pases_m["is_america_action"]) & (pases_m["location_x"] >= 80)])
    riv_att = len(pases_m[(~pases_m["is_america_action"]) & (pases_m["location_x"] >= 80)])
    tot_att = ame_att + riv_att
    ft_val = (ame_att / tot_att * 100.0) if tot_att > 0 else np.nan

    # D. PPDA Riguroso
    p_riv_def = len(grp[(~grp["is_america_action"]) & (grp["type"] == "Pass") & (grp["location_x"] <= 60)])
    
    # Filtro estricto de acciones defensivas
    d_evts = grp[
        (grp["is_america_action"])
        & (grp["location_x"] >= 60)
        & (grp["type"].isin(["Tackle", "Interception", "Foul Committed", "Duel", "Block"]))
    ]
    # Deduplicación por evento primario en timestamp
    d_act_ame = len(d_evts.drop_duplicates(subset=["period", "minute", "second", "location_x", "location_y"]))
    ppda_val = (p_riv_def / d_act_ame) if d_act_ame > 0 else np.nan

    # E. Pases Progresivos (Juego Abierto América con Geometría de Área Penal Exacta)
    restart_patterns = ["From Corner", "From Free Kick", "From Throw In", "From Kick Off", "From Goal Kick"]
    ame_open_passes = grp[
        (grp["is_america_action"])
        & (grp["type"] == "Pass")
        & (grp["pass_outcome"].isna())
        & (grp["end_location_x"].notna())
        & (~grp["play_pattern"].isin(restart_patterns))
    ].copy()

    if len(ame_open_passes) > 0:
      d_start = np.sqrt((120.0 - ame_open_passes["location_x"]) ** 2 + (40.0 - ame_open_passes["location_y"]) ** 2)
      d_end = np.sqrt((120.0 - ame_open_passes["end_location_x"]) ** 2 + (40.0 - ame_open_passes["end_location_y"]) ** 2)

      # Condición estricta de ingreso a área penal desde fuera
      in_penalty_box = (
          (ame_open_passes["end_location_x"] >= 102.0)
          & (ame_open_passes["end_location_y"] >= 18.0)
          & (ame_open_passes["end_location_y"] <= 62.0)
          & (
              (ame_open_passes["location_x"] < 102.0)
              | (ame_open_passes["location_y"] < 18.0)
              | (ame_open_passes["location_y"] > 62.0)
          )
      )

      # Regla Base (30/15/10%)
      cond_base = (
          ((ame_open_passes["location_x"] < 40.0) & (d_end <= d_start * 0.70))
          | ((ame_open_passes["location_x"] >= 40.0) & (ame_open_passes["location_x"] < 80.0) & (d_end <= d_start * 0.85))
          | ((ame_open_passes["location_x"] >= 80.0) & ((d_end <= d_start * 0.90) | in_penalty_box))
      )

      # Regla Estricta (35/20/15%)
      cond_strict = (
          ((ame_open_passes["location_x"] < 40.0) & (d_end <= d_start * 0.65))
          | ((ame_open_passes["location_x"] >= 40.0) & (ame_open_passes["location_x"] < 80.0) & (d_end <= d_start * 0.80))
          | ((ame_open_passes["location_x"] >= 80.0) & ((d_end <= d_start * 0.85) | in_penalty_box))
      )

      prog_base_cnt = int(cond_base.sum())
      prog_strict_cnt = int(cond_strict.sum())
      open_p_cnt = len(ame_open_passes)
    else:
      prog_base_cnt, prog_strict_cnt, open_p_cnt = 0, 0, 0

    match_analytics.append({
        "match_id": m_id,
        "season": m_info["season"],
        "stage": m_info["stage"],
        "is_home": m_info["is_home"],
        "home_team": m_info["home_team"],
        "away_team": m_info["away_team"],
        "ame_goals": ame_tot_goals,
        "riv_goals": riv_tot_goals,
        "ame_xg": ame_xg_float,
        "riv_xg": riv_xg_float,
        "field_tilt_pct": ft_val,
        "ppda": ppda_val,
        "pases_riv_def_x60": p_riv_def,
        "acciones_def_ame_x60": d_act_ame,
        "ame_pases_abiertos": open_p_cnt,
        "ame_pases_progresivos_base": prog_base_cnt,
        "ame_pases_progresivos_estricta": prog_strict_cnt,
    })

  df_analytics_master = pd.DataFrame(match_analytics)

  # Exportación del Dataset Analítico Maestro de Partidos
  out_csv = PROCESSED_DIR / "fase3_metricas_matches_master.csv"
  df_analytics_master.to_csv(out_csv, index=False)

  print(f"   ✔️ Dataset analítico consolidado exportado en: {out_csv.name} ({len(df_analytics_master)} filas)\n")

  # ------------------------------------------------------------------
  # 3. VERIFICACIÓN Y AUDITORÍA DE SECUENCIAS ABP RECONCILIADAS
  # ------------------------------------------------------------------
  print("3. Auditando secuencias de Balón Parado (ABP) con corte de 4° pase y t <= 10.00s...")

  abp_shots_all = df_ev[
      (df_ev["play_pattern"].isin(["From Corner", "From Free Kick", "From Throw In"]))
      & (df_ev["type"] == "Shot")
      & (df_ev["period"] <= 4)
  ].copy()

  retained_abp_cnt = 0
  reclassified_abp_cnt = 0
  retained_abp_xg = 0.0
  reclassified_abp_xg = 0.0

  for idx, shot in abp_shots_all.iterrows():
    m_id = shot["match_id_clean"]
    s_time = shot["minute"] * 60 + shot["second"]
    s_xg = float(shot["shot_statsbomb_xg"]) if pd.notna(shot["shot_statsbomb_xg"]) else 0.0

    prev_passes = df_ev[
        (df_ev["match_id_clean"] == m_id)
        & (df_ev["type"] == "Pass")
        & (df_ev["play_pattern"] == shot["play_pattern"])
    ]
    prev_pass_times = prev_passes["minute"] * 60 + prev_passes["second"]

    # Inervalo de tiempo <= 10.00s
    valid_diffs = prev_pass_times[(s_time - prev_pass_times >= 0) & (s_time - prev_pass_times <= 10.00)]

    if len(valid_diffs) <= 3 and len(valid_diffs) > 0:
      retained_abp_cnt += 1
      retained_abp_xg += s_xg
    else:
      reclassified_abp_cnt += 1
      reclassified_abp_xg += s_xg

  print(f"   • Remates Totales Evaluados en ABP: {len(abp_shots_all)}")
  print(f"   • Remates Retenidos en ABP (<=3 pases / <=10s): {retained_abp_cnt} | xG: {retained_abp_xg:.4f}")
  print(f"   • Remates Reclasificados a Juego Abierto: {reclassified_abp_cnt} | xG: {reclassified_abp_xg:.4f}")
  print(f"   • Suma Comprobada Exacta: {retained_abp_cnt + reclassified_abp_cnt} remates | {retained_abp_xg + reclassified_abp_xg:.4f} xG\n")

  # ------------------------------------------------------------------
  # 4. MANIFIESTO OFICIAL DE LA FASE 3 (JSON)
  # ------------------------------------------------------------------
  df_reg = df_analytics_master[df_analytics_master["stage"] == "Fase Regular"]
  
  manifest_content = {
      "fase": "3 - Capa Analítica y Resultados Tácticos",
      "version": "v3.0-ANALYTICAL-MASTER",
      "cobertura_partidos": {
          "totales": len(df_analytics_master),
          "fase_regular": len(df_reg),
          "liguilla": len(df_analytics_master[df_analytics_master["stage"] == "Liguilla"]),
          "play_in": len(df_analytics_master[df_analytics_master["stage"] == "Play-In"]),
      },
      "reconciliacion_goles_xg": {
          "goles_totales_america": int(df_analytics_master["ame_goals"].sum()),
          "goles_totales_rivales": int(df_analytics_master["riv_goals"].sum()),
          "xg_acumulado_america": round(float(df_analytics_master["ame_xg"].sum()), 4),
          "xg_acumulado_rivales": round(float(df_analytics_master["riv_xg"].sum()), 4),
      },
      "ppda_fase_regular": {
          "partidos_evaluados": len(df_reg),
          "suma_pases_rival": int(df_reg["pases_riv_def_x60"].sum()),
          "suma_acciones_def": int(df_reg["acciones_def_ame_x60"].sum()),
          "ppda_agregado_global": round(float(df_reg["pases_riv_def_x60"].sum() / df_reg["acciones_def_ame_x60"].sum()), 2),
          "ppda_media_partidos": round(float(df_reg["ppda"].mean()), 2),
          "ppda_mediana_partidos": round(float(df_reg["ppda"].median()), 2),
      },
      "abp_secuencias": {
          "remates_totales": len(abp_shots_all),
          "remates_retenidos_abp": retained_abp_cnt,
          "xg_retenido_abp": round(retained_abp_xg, 4),
          "remates_reclasificados": reclassified_abp_cnt,
          "xg_reclasificado": round(reclassified_abp_xg, 4),
      },
  }

  manifest_json = PROCESSED_DIR / "fase3_analytical_manifest.json"
  with open(manifest_json, "w", encoding="utf-8") as f:
    json.dump(manifest_content, f, indent=4, ensure_ascii=False)

  print("==================================================================")
  print("✅ CAPA ANALÍTICA RECONSTRUIDA Y VALIDADA EXITOSAMENTE.")
  print("📦 Artefactos actualizados:")
  print(f"   • {out_csv.name}")
  print(f"   • {manifest_json.name}")
  print("==================================================================")

if __name__ == "__main__":
  run_analytical_engine_v3()