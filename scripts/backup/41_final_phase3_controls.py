"""
Paso 41 (Corregido): Evidencia de Controles Finales de la Fase 3
Proyecto: El Vuelo del Bicampeón (ISAC 2026)
"""

import json
from pathlib import Path
import pandas as pd

DATA_DIR = Path(
    r"C:\Users\omarc\AI_Projects\Competitions\club-america-isac-2026\data"
)
PROCESSED_DIR = DATA_DIR / "processed"
RAW_DIR = DATA_DIR / "raw"


def run_final_phase3_controls():
  print("==================================================================")
  print("📊 EVIDENCIA DE CONTROLES FINALES - CAPA ANALÍTICA (FASE 3)")
  print("==================================================================\n")

  events_file = PROCESSED_DIR / "events_master.csv"
  index_json = RAW_DIR / "jardine_matches_index.json"

  if not events_file.exists():
    raise FileNotFoundError(f"❌ Error: {events_file} no existe.")

  df_ev = pd.read_csv(events_file, low_memory=False)
  df_ev["match_id_clean"] = (
      pd.to_numeric(
          df_ev["match_id"].astype(str).str.replace("match_", ""),
          errors="coerce",
      )
      .fillna(0)
      .astype("int64")
  )

  # ------------------------------------------------------------------
  # CONTROL 1: ABP - DESGLOSE POR PATRÓN DE REINICIO INICIAL
  # ------------------------------------------------------------------
  print("1. CONTROL 1: TABLA DE REMATES Y xG POR PATRÓN INICIAL DE ABP:")
  print("-" * 65)

  shots_reg = df_ev[(df_ev["type"] == "Shot") & (df_ev["period"] <= 4)].copy()

  abp_patterns = ["From Corner", "From Free Kick", "From Throw In"]
  abp_shots = shots_reg[shots_reg["play_pattern"].isin(abp_patterns)].copy()

  abp_summary = (
      abp_shots.groupby("play_pattern")
      .agg(
          remates=("event_id", "count"),
          xg_total=("shot_statsbomb_xg", lambda x: x.fillna(0.0).sum()),
          xg_promedio=("shot_statsbomb_xg", lambda x: x.fillna(0.0).mean()),
      )
      .reset_index()
  )

  print(abp_summary.to_string(index=False))

  official_733 = abp_summary[
      abp_summary["play_pattern"].isin(["From Corner", "From Free Kick"])
  ]
  print(
      f"\n• Estándar Oficial (Corner + Free Kick):"
      f" {official_733['remates'].sum()} remates |"
      f" {official_733['xg_total'].sum():.4f} xG"
  )
  
  throw_in_row = abp_summary[abp_summary["play_pattern"] == "From Throw In"]
  if not throw_in_row.empty:
    print(
        f"• Población Diferenciada (Throw In):"
        f" {throw_in_row['remates'].values[0]} remates |"
        f" {throw_in_row['xg_total'].values[0]:.4f} xG\n"
    )

  # ------------------------------------------------------------------
  # CONTROL 2: PPDA - VERIFICACIÓN DE ACCIONES Y DEDUPLICACIÓN
  # ------------------------------------------------------------------
  print("2. CONTROL 2: SUMAS DE PPDA Y DEDUPLICACIÓN DE ACCIONES DEFENSIVAS:")
  print("-" * 65)

  with open(index_json, "r", encoding="utf-8") as f:
    meta_raw = json.load(f)

  reg_matches_ids = []
  for m in meta_raw:
    m_id = int(str(m.get("match_id", 0)).replace("match_", ""))
    stage_raw = str(m.get("competition_stage", "")).lower()
    if (
        ("regular" in stage_raw or stage_raw in ["apertura", "clausura"])
        and not ("quarter" in stage_raw or "semi" in stage_raw or "final" in stage_raw)
        and "play-off" not in stage_raw
        and "play-in" not in stage_raw
    ):
      reg_matches_ids.append(m_id)

  df_reg = df_ev[
      (df_ev["match_id_clean"].isin(reg_matches_ids)) & (df_ev["period"] <= 4)
  ]

  pases_riv = len(
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

  total_def_bruto = len(def_evts)
  def_dedup = len(
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
  duplicados_eliminados = total_def_bruto - def_dedup

  print(f"• Total Partidos de Fase Regular: {len(reg_matches_ids)}")
  print(f"• Pases Intentados Rival (X <= 60): {pases_riv:,}")
  print(f"• Acciones Defensivas América Brutas (X >= 60): {total_def_bruto:,}")
  print(
      "• Acciones Defensivas América Deduplicadas (X >="
      f" 60): {def_dedup:,} (Duplicados filtrados: {duplicados_eliminados})"
  )
  print(f"• PPDA Agregado Global (Suma/Suma): {pases_riv / def_dedup:.2f}\n")

  # ------------------------------------------------------------------
  # CONTROL 3: GOLES - REPORTE DE CASOS ESPECIALES Y AUTOGOLES
  # ------------------------------------------------------------------
  print("3. CONTROL 3: CASOS ESPECIALES DE GOLES (AUTOGOLES Y PENALTIS):")
  print("-" * 65)

  # Filtrado seguro de penaltis en tiempo regular
  if "shot_type" in shots_reg.columns:
    penalties_reg = shots_reg[
        (shots_reg["shot_outcome"].isin(["Goal", "Goal_Penalty"]))
        & (shots_reg["shot_type"] == "Penalty")
    ]
  elif "shot_outcome" in shots_reg.columns:
    penalties_reg = shots_reg[
        shots_reg["shot_outcome"].isin(["Goal_Penalty"])
        | (
            (shots_reg["shot_outcome"] == "Goal")
            & (shots_reg["type"] == "Penalty")
        )
    ]
  else:
    penalties_reg = shots_reg[shots_reg["type"] == "Penalty"]

  # Filtrado seguro de autogoles
  if "pass_type" in df_ev.columns:
    own_goals = df_ev[
        (df_ev["period"] <= 4) & (df_ev["pass_type"] == "Own Goal")
    ]
  elif "type" in df_ev.columns:
    own_goals = df_ev[(df_ev["period"] <= 4) & (df_ev["type"] == "Own Goal")]
  else:
    own_goals = pd.DataFrame()

  print(f"• Penaltis Convertidos en Tiempo Regular (period <= 4): {len(penalties_reg)}")
  print(f"• Autogoles Registrados en el Dataset (period <= 4): {len(own_goals)}")

  if len(own_goals) > 0:
    print("\n📋 Detalle de Autogoles Auditados:")
    cols_to_show = [c for c in ["match_id_clean", "period", "minute", "second", "team", "is_america_action"] if c in own_goals.columns]
    print(own_goals[cols_to_show].to_string(index=False))

  print(
      "\n=================================================================="
  )
  print("✅ EVIDENCIA DE CONTROLES COMPLETADA EXITOSAMENTE.")
  print("==================================================================")


if __name__ == "__main__":
  run_final_phase3_controls()