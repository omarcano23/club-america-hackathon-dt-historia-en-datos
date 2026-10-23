"""
Paso 36 (Corregido): Inspección Fila por Fila y Auditoría Forense
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


def run_row_level_check():
  print("==================================================================")
  print("🔬 AUDITORÍA FORENSE DE FILAS INDIVIDUALES (RECONCILIACIÓN FINAL)")
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
  # 1. PPDA: RECALCULO DIRECTO SOBRE LAS 66 FILAS CANÓNICAS
  # ------------------------------------------------------------------
  print("1. INSPECCIÓN FORENSE DE LAS 66 FILAS CANÓNICAS DE PPDA:")
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

  match_rows = []
  for m_id in reg_matches_ids:
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

  tot_pases = df_66["pases_riv"].sum()
  tot_def = df_66["def_act"].sum()
  mean_ppda = df_66["ppda_individual"].mean()
  median_ppda = df_66["ppda_individual"].median()
  min_ppda_row = df_66.loc[df_66["ppda_individual"].idxmin()]
  max_ppda_row = df_66.loc[df_66["ppda_individual"].idxmax()]

  print(f"- Número exacto de filas procesadas: {len(df_66)}")
  print(
      f"- Suma de Numeradores (Pases Rival X<=60): {tot_pases:,} (Promedio:"
      f" {tot_pases / len(df_66):.2f})"
  )
  print(
      f"- Suma de Denominadores (Acciones América X>=60): {tot_def:,} (Promedio:"
      f" {tot_def / len(df_66):.2f})"
  )
  print(f"- PPDA Agregado Global ({tot_pases:,} / {tot_def:,}): {tot_pases / tot_def:.2f}")
  print(f"- Media Real Reconciliada (ppda_individual.mean()): {mean_ppda:.2f}")
  print(f"- Mediana Real Reconciliada (ppda_individual.median()): {median_ppda:.2f}")
  print(
      f"- PPDA Mínimo (Mayor Presión): {min_ppda_row['ppda_individual']:.2f}"
      f" (Match ID: {int(min_ppda_row['match_id'])})"
  )
  print(
      f"- PPDA Máximo (Menor Presión): {max_ppda_row['ppda_individual']:.2f}"
      f" (Match ID: {int(max_ppda_row['match_id'])})\n"
  )

  # ------------------------------------------------------------------
  # 2. TABLA CRUZADA / DESGLOSE DE REINICIOS
  # ------------------------------------------------------------------
  print("2. TABLA Y CONTEO DE PATRONES DE REINICIO (PASES COMPLETADOS):")
  print("-" * 65)

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
  restarts_df = completed_passes[
      completed_passes["play_pattern"].isin(restart_patterns)
  ].copy()

  # Verificación segura de columna pass_type
  if "pass_type" in restarts_df.columns:
    col_type = restarts_df["pass_type"].fillna("Juego Fluido / Normal")
    crosstab_restarts = pd.crosstab(
        restarts_df["play_pattern"], col_type, margins=True
    )
    print(crosstab_restarts.to_string())
  else:
    print("📋 Conteos directos por play_pattern (columna 'pass_type' no presente en CSV):")
    counts_pattern = restarts_df["play_pattern"].value_counts()
    print(counts_pattern.to_string())

  tot_restarts = len(restarts_df)
  tot_open = len(completed_passes) - tot_restarts
  print(f"\n- Total Pases de Reinicio Excluidos: {tot_restarts:,}")
  print(f"- Total Pases de Juego Abierto Evaluados: {tot_open:,}\n")

  # ------------------------------------------------------------------
  # 3. ABP: AUDITORÍA DE REMATES REMATE POR REMATE (733 FILAS)
  # ------------------------------------------------------------------
  print("3. INSPECCIÓN INDIVIDUAL DE REMATES ABP (733 REMATES):")
  print("-" * 65)

  abp_shots = df_ev[
      (df_ev["play_pattern"].isin(["From Corner", "From Free Kick"]))
      & (df_ev["type"] == "Shot")
  ].copy()

  shot_records = []
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

    valid_origin = prev_pass_times[
        (s_time - prev_pass_times >= 0) & (s_time - prev_pass_times <= 10.0)
    ]
    pass_count = len(valid_origin)

    if pass_count <= 3:
      cat = "ABP_Retenido"
      reason = "Secuencia <= 3 pases y <= 10s"
    else:
      cat = "Juego_Abierto_Reclasificado"
      reason = "Exceso de pases (>= 4 pases)"

    shot_records.append({
        "match_id": m_id,
        "event_id": shot["event_id"],
        "xg": s_xg,
        "pases_previos": pass_count,
        "categoria": cat,
        "razon": reason,
    })

  df_shots_audit = pd.DataFrame(shot_records)

  abp_ret = df_shots_audit[df_shots_audit["categoria"] == "ABP_Retenido"]
  abp_rec = df_shots_audit[
      df_shots_audit["categoria"] == "Juego_Abierto_Reclasificado"
  ]

  print(f"- Total Remates ABP Inspeccionados: {len(df_shots_audit)}")
  print(
      f"- Remates Retenidos en ABP: {len(abp_ret)} | xG Suma Exacta:"
      f" {abp_ret['xg'].sum():.2f} (Promedio: {abp_ret['xg'].mean():.4f})"
  )
  print(
      f"- Remates Reclasificados a Juego Abierto: {len(abp_rec)} | xG Suma"
      f" Exacta: {abp_rec['xg'].sum():.2f} (Promedio: {abp_rec['xg'].mean():.4f})"
  )
  print(
      f"- Suma Comprobada: {len(abp_ret)} + {len(abp_rec)} ="
      f" {len(df_shots_audit)} | {abp_ret['xg'].sum():.2f} +"
      f" {abp_rec['xg'].sum():.2f} = {df_shots_audit['xg'].sum():.2f} xG"
  )

  # Actualizar entregables
  final_manifest = {
      "fase": "2.3 - Puerta de Aceptación Metodológica Reconciliada",
      "version": "v1.0-CONSOLIDATED",
      "ppda_fase_regular": {
          "partidos": len(df_66),
          "suma_pases_rival": int(tot_pases),
          "suma_acciones_def": int(tot_def),
          "ppda_agregado": round(float(tot_pases / tot_def), 2),
          "ppda_media": round(float(mean_ppda), 2),
          "ppda_mediana": round(float(median_ppda), 2),
      },
      "pases_progresivos": {
          "pases_completados": len(completed_passes),
          "reinicios_excluidos": tot_restarts,
          "pases_juego_abierto": tot_open,
      },
      "balon_parado_abp": {
          "remates_totales": len(df_shots_audit),
          "remates_retenidos_abp": len(abp_ret),
          "xg_retenido_abp": round(float(abp_ret["xg"].sum()), 2),
          "remates_reclasificados": len(abp_rec),
          "xg_reclasificado": round(float(abp_rec["xg"].sum()), 2),
          "total_xg": round(float(df_shots_audit["xg"].sum()), 2),
      },
  }

  out_json = PROCESSED_DIR / "audit_phase2_final.json"
  with open(out_json, "w", encoding="utf-8") as f:
    json.dump(final_manifest, f, indent=4, ensure_ascii=False)

  print("\n==================================================================")
  print("⚙️ EJECUCIÓN CONCLUIDA. DATOS Y ARTEFACTOS ACTUALIZADOS.")
  print("==================================================================")


if __name__ == "__main__":
  run_row_level_check()