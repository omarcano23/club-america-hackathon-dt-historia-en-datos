"""
Paso 37: Comprobación de Integridad de Filas Canónicas PPDA y Límite Temporal ABP
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


def run_boundary_check():
  print("==================================================================")
  print("🔬 VERIFICACIÓN DE INTEGRIDAD DE FILAS PPDA Y LÍMITE TEMPORAL ABP")
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

  # ------------------------------------------------------------------
  # COMPROBACIÓN A: UNICIDAD Y NO DUPLICIDAD DE LAS 66 FILAS CANÓNICAS
  # ------------------------------------------------------------------
  print("A. COMPROBACIÓN DE UNICIDAD EN LAS 66 FILAS DE FASE REGULAR:")
  print("-" * 65)

  with open(index_json, "r", encoding="utf-8") as f:
    meta_data = json.load(f)

  reg_matches_ids = []
  for m in meta_data:
    m_id = int(str(m.get("match_id", 0)).replace("match_", ""))
    stage_raw = str(m.get("competition_stage", "")).lower()
    if (
        ("regular" in stage_raw or stage_raw in ["apertura", "clausura"])
        and not ("quarter" in stage_raw or "semi" in stage_raw or "final" in stage_raw)
        and "play-off" not in stage_raw
        and "play-in" not in stage_raw
    ):
      reg_matches_ids.append(m_id)

  # Verificar duplicados en la lista de IDs seleccionados
  unique_reg_ids = list(set(reg_matches_ids))
  print(f"- Total de match_id extraídos del índice: {len(reg_matches_ids)}")
  print(f"- Total de match_id ÚNICOS (sin duplicados): {len(unique_reg_ids)}")

  match_rows = []
  for m_id in unique_reg_ids:
    grp = df_ev[
        (df_ev["match_id_clean"] == m_id) & (df_ev["period"] <= 4)
    ].copy()

    pases_riv = len(
        grp[
            (~grp["is_america_action"])
            & (grp["type"] == "Pass")
            & (grp["location_x"] <= 60)
        ]
    )

    def_evts = grp[
        (grp["is_america_action"])
        & (grp["location_x"] >= 60)
        & (
            grp["type"].isin(
                ["Tackle", "Interception", "Foul Committed", "Duel", "Block"]
            )
        )
    ]
    def_act = len(
        def_evts.drop_duplicates(
            subset=["period", "minute", "second", "location_x", "location_y"]
        )
    )

    ppda_val = (pases_riv / def_act) if def_act > 0 else np.nan
    match_rows.append({
        "match_id": m_id,
        "pases_riv": pases_riv,
        "def_act": def_act,
        "ppda_individual": ppda_val,
    })

  df_66 = pd.DataFrame(match_rows)

  null_count = df_66["ppda_individual"].isna().sum()
  duplicate_matches = df_66["match_id"].duplicated().sum()

  print(f"- Registros con PPDA Nulo (NaN): {null_count}")
  print(f"- Coincidencia de duplicados en el DataFrame: {duplicate_matches}")
  print(
      f"- Media dinámica calculada en el vector ({len(df_66)} filas):"
      f" {df_66['ppda_individual'].mean():.4f}"
  )
  print(
      f"- Mediana dinámica calculada en el vector ({len(df_66)} filas):"
      f" {df_66['ppda_individual'].median():.4f}\n"
  )

  # ------------------------------------------------------------------
  # COMPROBACIÓN B: CASOS LÍMITE (9.99s, 10.00s, 10.01s) Y NO DUPLICIDAD EN ABP
  # ------------------------------------------------------------------
  print("B. PRUEBA DE BORDES EN REMATES ABP Y UNICIDAD DE EVENTOS:")
  print("-" * 65)

  abp_shots = df_ev[
      (df_ev["play_pattern"].isin(["From Corner", "From Free Kick"]))
      & (df_ev["type"] == "Shot")
  ].copy()

  print(f"- Total de remates ABP extraídos: {len(abp_shots)}")
  print(
      f"- Unicidad de event_id de remates (duplicados):"
      f" {abp_shots['event_id'].duplicated().sum()}"
  )

  shots_detail = []
  shots_near_boundary = 0

  for idx, shot in abp_shots.iterrows():
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

    # Diferencias de tiempo respecto al cobro
    diffs = s_time - prev_pass_times
    valid_diffs = diffs[(diffs >= 0) & (diffs <= 10.00)]
    
    # Identificar remates en la frontera estrecha (entre 9.5s y 10.5s)
    boundary_diffs = diffs[(diffs >= 9.50) & (diffs <= 10.50)]
    if len(boundary_diffs) > 0:
      shots_near_boundary += 1

    pass_count = len(valid_diffs)
    is_retained = (pass_count <= 3)

    shots_detail.append({
        "event_id": shot["event_id"],
        "match_id": m_id,
        "xg": s_xg,
        "pases_previos": pass_count,
        "is_retained": is_retained,
    })

  df_shots = pd.DataFrame(shots_detail)

  retained_df = df_shots[df_shots["is_retained"]]
  reclassified_df = df_shots[~df_shots["is_retained"]]

  print(f"- Remates cercanos a la frontera de 10.00s (9.5s - 10.5s): {shots_near_boundary}")
  print(f"- Remates Retenidos (<= 10.00s Y <= 3 pases): {len(retained_df)} | xG: {retained_df['xg'].sum():.4f}")
  print(f"- Remates Reclasificados (> 10.00s O > 3 pases): {len(reclassified_df)} | xG: {reclassified_df['xg'].sum():.4f}")
  print(f"- Suma total de remates verificados: {len(df_shots)} | xG Total: {df_shots['xg'].sum():.4f}\n")

  print("==================================================================")
  print("⚙️ VERIFICACIÓN FINALIZADA. COMPRUEBA LOS CONTEOS IMPRESOS.")
  print("==================================================================")


if __name__ == "__main__":
  run_boundary_check()