"""
Fase 3 - Paso 3.1 & 3.2: Construcción y Validación de la Capa Analítica
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


def build_analytical_layer():
  print("==================================================================")
  print("🚀 FASE 3: CONSTRUCCIÓN Y VALIDACIÓN DE LA CAPA ANALÍTICA")
  print("==================================================================\n")

  events_file = PROCESSED_DIR / "events_master.csv"
  index_json = RAW_DIR / "jardine_matches_index.json"

  if not events_file.exists():
    print(f"❌ Error: {events_file} no existe.")
    return

  # 1. CARGA Y NORMALIZACIÓN DE FUENTES
  print("1. Normalizando datos e identificadores clave...")
  df_ev = pd.read_csv(events_file, low_memory=False)

  # Normalización estricta de match_id
  df_ev["match_id_clean"] = (
      pd.to_numeric(
          df_ev["match_id"].astype(str).str.replace("match_", ""),
          errors="coerce",
      )
      .fillna(0)
      .astype("int64")
  )

  # Mapeo de Metadatos de Partidos y Fases Canónicas
  with open(index_json, "r", encoding="utf-8") as f:
    meta_data = json.load(f)

  meta_dict = {}
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

  print(
      f"   ✔️ Total de eventos procesados: {len(df_ev):,} en"
      f" {df_ev['match_id_clean'].nunique()} partidos.\n"
  )

  # 2. CONTROLES ESPECÍFICOS DE VALIDACIÓN DE DATOS (NIVEL CÁLCULO)
  print("2. Ejecutando controles automatizados de reconciliación...")

  # Control A: Goles y Tiros
  shots_df = df_ev[(df_ev["type"] == "Shot") & (df_ev["period"] <= 4)].copy()
  goals_df = shots_df[
      shots_df["shot_outcome"].isin(["Goal", "Goal_Penalty"])
      | (shots_df["type"] == "Goal")
  ]

  tot_shots = len(shots_df)
  tot_goals = len(goals_df)
  tot_xg = shots_df["shot_statsbomb_xg"].sum()

  print(f"   • Control A - Tiros Totales en Reglam. (<=4 per): {tot_shots:,}")
  print(
      f"   • Control A - Goles Registrados en Eventos: {tot_goals} (xG"
      f" Acumulado Total: {tot_xg:.2f})"
  )

  # Control B: Numeradores y Denominadores de PPDA
  reg_matches = [
      m_id for m_id, info in meta_dict.items() if info["stage"] == "Fase Regular"
  ]
  df_reg = df_ev[
      (df_ev["match_id_clean"].isin(reg_matches)) & (df_ev["period"] <= 4)
  ].copy()

  pases_riv_x60 = len(
      df_reg[
          (~df_reg["is_america_action"])
          & (df_reg["type"] == "Pass")
          & (df_reg["location_x"] <= 60)
      ]
  )
  def_evts = df_reg[
      (df_reg["is_america_action"])
      & (df_reg["location_x"] >= 60)
      & (
          df_reg["type"].isin(
              ["Tackle", "Interception", "Foul Committed", "Duel", "Block"]
          )
      )
  ]
  def_act_ame = len(
      def_evts.drop_duplicates(
          subset=[
              "match_id_clean",
              "period",
              "minute",
              "second",
              "location_x",
              "location_y",
          ]
      )
  )

  print(
      f"   • Control B - PPDA Fase Regular (66 partidos): Pases Rival"
      f" {pases_riv_x60:,} / Acciones Def. América {def_act_ame:,} ->"
      f" Agregado = {pases_riv_x60 / def_act_ame:.2f}"
  )

  # Control C: Balón Parado (ABP) y Remates Unívocos
  abp_shots = df_ev[
      (df_ev["play_pattern"].isin(["From Corner", "From Free Kick"]))
      & (df_ev["type"] == "Shot")
      & (df_ev["period"] <= 4)
  ].copy()
  tot_abp_shots = len(abp_shots)
  dup_abp_shots = abp_shots["event_id"].duplicated().sum()

  print(
      f"   • Control C - Remates de Balón Parado: {tot_abp_shots} remates"
      f" (Duplicados detectados: {dup_abp_shots})\n"
  )

  # 3. GENERACIÓN DE TABLAS ANALÍTICAS CONSOLIDADAS
  print("3. Generando tablas analíticas versionadas (fase3_metricas_matches.csv)...")

  match_records = []
  for m_id, grp in df_ev[df_ev["period"] <= 4].groupby("match_id_clean"):
    m_info = meta_dict.get(
        m_id,
        {
            "season": "Desconocida",
            "stage": "Fase Regular",
            "is_home": False,
            "home_team": "Rival",
            "away_team": "Rival",
        },
    )

    # Goles y xG
    m_shots = grp[grp["type"] == "Shot"]
    ame_shots = m_shots[m_shots["is_america_action"]]
    riv_shots = m_shots[~m_shots["is_america_action"]]

    ame_goals = len(ame_shots[ame_shots["shot_outcome"] == "Goal"])
    riv_goals = len(riv_shots[riv_shots["shot_outcome"] == "Goal"])
    ame_xg = ame_shots["shot_statsbomb_xg"].sum()
    riv_xg = riv_shots["shot_statsbomb_xg"].sum()

    # Field Tilt
    pases_m = grp[(grp["type"] == "Pass") & (grp["pass_outcome"].isna())]
    ame_att = len(
        pases_m[(pases_m["is_america_action"]) & (pases_m["location_x"] >= 80)]
    )
    riv_att = len(
        pases_m[(~pases_m["is_america_action"]) & (pases_m["location_x"] >= 80)]
    )
    tot_att = ame_att + riv_att
    ft_val = (ame_att / tot_att * 100) if tot_att > 0 else np.nan

    # PPDA
    p_riv_def = len(
        grp[
            (~grp["is_america_action"])
            & (grp["type"] == "Pass")
            & (grp["location_x"] <= 60)
        ]
    )
    d_evts = grp[
        (grp["is_america_action"])
        & (grp["location_x"] >= 60)
        & (
            grp["type"].isin(
                ["Tackle", "Interception", "Foul Committed", "Duel", "Block"]
            )
        )
    ]
    d_act_ame = len(
        d_evts.drop_duplicates(
            subset=["period", "minute", "second", "location_x", "location_y"]
        )
    )
    ppda_val = (p_riv_def / d_act_ame) if d_act_ame > 0 else np.nan

    # Pases Progresivos (Juego Abierto América)
    restart_patterns = [
        "From Corner",
        "From Free Kick",
        "From Throw In",
        "From Kick Off",
        "From Goal Kick",
    ]
    ame_open_passes = grp[
        (grp["is_america_action"])
        & (grp["type"] == "Pass")
        & (grp["pass_outcome"].isna())
        & (grp["end_location_x"].notna())
        & (~grp["play_pattern"].isin(restart_patterns))
    ].copy()

    if len(ame_open_passes) > 0:
      d_start = np.sqrt(
          (120 - ame_open_passes["location_x"]) ** 2
          + (40 - ame_open_passes["location_y"]) ** 2
      )
      d_end = np.sqrt(
          (120 - ame_open_passes["end_location_x"]) ** 2
          + (40 - ame_open_passes["end_location_y"]) ** 2
      )

      cond_base = (
          (ame_open_passes["location_x"] < 40) & (d_end <= d_start * 0.70)
      ) | (
          (ame_open_passes["location_x"] >= 40)
          & (ame_open_passes["location_x"] < 80)
          & (d_end <= d_start * 0.85)
      ) | (
          (ame_open_passes["location_x"] >= 80)
          & (
              (d_end <= d_start * 0.90)
              | (ame_open_passes["end_location_x"] >= 102)
          )
      )

      prog_base_ame = int(cond_base.sum())
      open_p_ame_cnt = len(ame_open_passes)
    else:
      prog_base_ame, open_p_ame_cnt = 0, 0

    match_records.append({
        "match_id": m_id,
        "season": m_info["season"],
        "stage": m_info["stage"],
        "is_home": m_info["is_home"],
        "home_team": m_info["home_team"],
        "away_team": m_info["away_team"],
        "ame_goals": ame_goals,
        "riv_goals": riv_goals,
        "ame_xg": round(float(ame_xg), 2),
        "riv_xg": round(float(riv_xg), 2),
        "field_tilt_pct": round(float(ft_val), 2) if pd.notna(ft_val) else np.nan,
        "ppda": round(float(ppda_val), 2) if pd.notna(ppda_val) else np.nan,
        "pases_riv_def_x60": p_riv_def,
        "acciones_def_ame_x60": d_act_ame,
        "ame_pases_abiertos": open_p_ame_cnt,
        "ame_pases_progresivos": prog_base_ame,
    })

  df_f3_matches = pd.DataFrame(match_records)
  out_csv = PROCESSED_DIR / "fase3_metricas_matches.csv"
  df_f3_matches.to_csv(out_csv, index=False)

  print(
      f"   ✔️ Tabla analítica generada con éxito: {out_csv.name} ({len(df_f3_matches)} filas)\n"
  )

  # 4. EXPORTAR MANIFIESTO Y RESULTADOS DE VALIDACIÓN (JSON)
  manifest_content = {
      "fase": "3 - Capa Analítica y Resultados Tácticos",
      "version": "v3.0-ANALYTICAL-LAYER",
      "partidos_totales": len(df_f3_matches),
      "fase_regular": len(df_f3_matches[df_f3_matches["stage"] == "Fase Regular"]),
      "liguilla": len(df_f3_matches[df_f3_matches["stage"] == "Liguilla"]),
      "play_in": len(df_f3_matches[df_f3_matches["stage"] == "Play-In"]),
      "controles_fase3": {
          "tiros_totales_reglamento": tot_shots,
          "goles_totales_reglamento": tot_goals,
          "xg_acumulado_total": round(float(tot_xg), 2),
          "ppda_fase_regular_agregado": round(float(pases_riv_x60 / def_act_ame), 2),
          "remates_abp_unicos": tot_abp_shots,
      },
  }

  manifest_json = PROCESSED_DIR / "fase3_analytical_manifest.json"
  with open(manifest_json, "w", encoding="utf-8") as f:
    json.dump(manifest_content, f, indent=4, ensure_ascii=False)

  print("==================================================================")
  print("✅ PASO 3.1 & 3.2 COMPLETADOS EXITOSAMENTE.")
  print(f"📦 Artefactos de la Capa Analítica:")
  print(f"   • {out_csv.name}")
  print(f"   • {manifest_json.name}")
  print("==================================================================")


if __name__ == "__main__":
  build_analytical_layer()