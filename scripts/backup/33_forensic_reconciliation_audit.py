"""
Paso 34: Reconciliación 100% Dinámica y Calculada desde Datos
Proyecto: El Vuelo del Bicampeón (ISAC 2026)
"""

import json
from pathlib import Path
import numpy as np
import pandas as pd

# Rutas del proyecto
DATA_DIR = Path(
    r"C:\Users\omarc\AI_Projects\Competitions\club-america-isac-2026\data"
)
PROCESSED_DIR = DATA_DIR / "processed"
RAW_DIR = DATA_DIR / "raw"


def run_dynamic_reconciliation():
  print("==================================================================")
  print("🔬 EJECUTANDO CÁLCULO DINO Y RECONCILIACIÓN DINÁMICA (SIN HARDCODING)")
  print("==================================================================\n")

  events_file = PROCESSED_DIR / "events_master.csv"
  index_json = RAW_DIR / "jardine_matches_index.json"

  if not events_file.exists():
    print(f"❌ Error: {events_file} no existe.")
    return

  # 1. Cargar datos
  df_ev = pd.read_csv(events_file, low_memory=False)
  df_ev["match_id_clean"] = (
      pd.to_numeric(
          df_ev["match_id"].astype(str).str.replace("match_", ""),
          errors="coerce",
      )
      .fillna(0)
      .astype("int64")
  )

  # Cargar mapa de fases de forma dinámica desde el índice JSON
  with open(index_json, "r", encoding="utf-8") as f:
    meta_data = json.load(f)

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
    elif "play-off" in stage_raw or "play-in" in stage_raw:
      stage_clean = "Play-In"
    else:
      stage_clean = "Liguilla"
    meta_stage_map[m_id] = stage_clean

  # ------------------------------------------------------------------
  # 1. CÁLCULO DINÁMICO POR PARTIDO (FIELD TILT Y PPDA)
  # ------------------------------------------------------------------
  print("1. Calculando Field Tilt y PPDA dinámicamente por partido...")
  match_rows = []

  for m_id, grp in df_ev[df_ev["period"] <= 4].groupby("match_id_clean"):
    stage = meta_stage_map.get(m_id, "Fase Regular")

    # Field Tilt
    pases = grp[(grp["type"] == "Pass") & (grp["pass_outcome"].isna())]
    ame_att = len(
        pases[(pases["is_america_action"]) & (pases["location_x"] >= 80)]
    )
    riv_att = len(
        pases[(~pases["is_america_action"]) & (pases["location_x"] >= 80)]
    )
    tot_att = ame_att + riv_att
    ft_val = (ame_att / tot_att * 100) if tot_att > 0 else np.nan

    # PPDA
    pases_riv_def = len(
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
    def_actions_ame = len(
        def_evts.drop_duplicates(
            subset=["period", "minute", "second", "location_x", "location_y"]
        )
    )

    ppda_val = (
        (pases_riv_def / def_actions_ame) if def_actions_ame > 0 else np.nan
    )

    match_rows.append({
        "match_id": m_id,
        "stage": stage,
        "pases_riv_x60": pases_riv_def,
        "def_actions_ame_x60": def_actions_ame,
        "ppda_individual": ppda_val,
        "field_tilt_pct": ft_val,
        "pases_att_ame": ame_att,
        "pases_att_riv": riv_att,
    })

  df_m = pd.DataFrame(match_rows)

  # Exportar metricas_master.csv calculado dinámicamente
  csv_out = PROCESSED_DIR / "metricas_master.csv"
  df_m.to_csv(csv_out, index=False)

  # Estadísticos calculados dinámicamente para Fase Regular
  df_reg = df_m[df_m["stage"] == "Fase Regular"]
  cnt_reg_matches = len(df_reg)
  tot_pases_riv = int(df_reg["pases_riv_x60"].sum())
  tot_def_actions = int(df_reg["def_actions_ame_x60"].sum())
  zero_denom_count = int((df_reg["def_actions_ame_x60"] == 0).sum())

  mean_ppda_reg = float(df_reg["ppda_individual"].mean())
  median_ppda_reg = float(df_reg["ppda_individual"].median())
  agg_ppda_reg = float(tot_pases_riv / tot_def_actions)

  mean_ft_reg = float(df_reg["field_tilt_pct"].mean())
  median_ft_reg = float(df_reg["field_tilt_pct"].median())

  print(f"   ✔️ Partidos de Fase Regular calculados: {cnt_reg_matches}")
  print(f"   ✔️ Denominadores en cero: {zero_denom_count}")
  print(
      f"   ✔️ PPDA Fase Regular -> Media: {mean_ppda_reg:.2f} | Mediana:"
      f" {median_ppda_reg:.2f} | Agregado: {agg_ppda_reg:.2f}"
  )

  # ------------------------------------------------------------------
  # 2. CÁLCULO DINÁMICO DE PASES PROGRESIVOS Y SENSIBILIDAD
  # ------------------------------------------------------------------
  print("\n2. Calculando pases progresivos dinámicamente desde eventos...")
  completed_passes_all = df_ev[
      (df_ev["type"] == "Pass") & (df_ev["pass_outcome"].isna())
  ].copy()

  restart_patterns = [
      "From Corner",
      "From Free Kick",
      "From Throw In",
      "From Kick Off",
      "From Goal Kick",
  ]
  is_restart = completed_passes_all["play_pattern"].isin(restart_patterns)

  restarts_passes = completed_passes_all[is_restart]
  open_play_passes = completed_passes_all[~is_restart].copy()

  tot_completed = len(completed_passes_all)
  tot_restarts = len(restarts_passes)
  tot_open_play = len(open_play_passes)

  # Vectores de distancia euclidiana
  d_start = np.sqrt(
      (120 - open_play_passes["location_x"]) ** 2
      + (40 - open_play_passes["location_y"]) ** 2
  )
  d_end = np.sqrt(
      (120 - open_play_passes["end_location_x"]) ** 2
      + (40 - open_play_passes["end_location_y"]) ** 2
  )

  cond_base = (
      (open_play_passes["location_x"] < 40) & (d_end <= d_start * 0.70)
  ) | (
      (open_play_passes["location_x"] >= 40)
      & (open_play_passes["location_x"] < 80)
      & (d_end <= d_start * 0.85)
  ) | (
      (open_play_passes["location_x"] >= 80)
      & ((d_end <= d_start * 0.90) | (open_play_passes["end_location_x"] >= 102))
  )

  cond_strict = (
      (open_play_passes["location_x"] < 40) & (d_end <= d_start * 0.65)
  ) | (
      (open_play_passes["location_x"] >= 40)
      & (open_play_passes["location_x"] < 80)
      & (d_end <= d_start * 0.80)
  ) | (
      (open_play_passes["location_x"] >= 80)
      & ((d_end <= d_start * 0.85) | (open_play_passes["end_location_x"] >= 102))
  )

  prog_base_cnt = int(cond_base.sum())
  prog_strict_cnt = int(cond_strict.sum())

  pct_prog_base = float(prog_base_cnt / tot_open_play * 100)
  pct_prog_strict = float(prog_strict_cnt / tot_open_play * 100)

  print(f"   ✔️ Pases completados totales: {tot_completed:,}")
  print(f"   ✔️ Pases de reinicio excluidos: {tot_restarts:,}")
  print(f"   ✔️ Pases en Juego Abierto: {tot_open_play:,}")
  print(f"   ✔️ Progresivos Regla Base: {prog_base_cnt:,} ({pct_prog_base:.2f}%)")
  print(
      f"   ✔️ Progresivos Regla Estricta: {prog_strict_cnt:,}"
      f" ({pct_prog_strict:.2f}%)"
  )

  # ------------------------------------------------------------------
  # 3. CÁLCULO DINÁMICO DE TRANSICIONES DEFENSIVAS ($R_{10}$)
  # ------------------------------------------------------------------
  print(
      "\n3. Clasificando transiciones defensivas (R10) dinámicamente desde"
      " pérdidas..."
  )
  turnovers = df_ev[
      (df_ev["is_america_action"])
      & (df_ev["period"] <= 4)
      & (
          (df_ev["pass_outcome"].isin(["Incomplete", "Out", "Pass Offside"]))
          | (df_ev["type"].isin(["Dispossessed", "Error"]))
      )
  ].copy()

  tot_turnovers = len(turnovers)
  c_rec, c_foul, c_shot, c_cont = 0, 0, 0, 0

  for idx, to in turnovers.iterrows():
    m_id = to["match_id_clean"]
    to_time = to["minute"] * 60 + to["second"]

    win_evts = df_ev[
        (df_ev["match_id_clean"] == m_id) & (df_ev["period"] <= 4)
    ].copy()
    win_evts["evt_time"] = win_evts["minute"] * 60 + win_evts["second"]

    sub_win = win_evts[
        (win_evts["evt_time"] - to_time > 0)
        & (win_evts["evt_time"] - to_time <= 10.0)
    ].sort_values(["evt_time", "index"])

    if len(sub_win) == 0:
      c_cont += 1
      continue

    assigned = False
    for _, evt in sub_win.iterrows():
      if evt["is_america_action"] and evt["type"] in [
          "Interception",
          "Tackle",
          "Ball Recovery",
      ]:
        c_rec += 1
        assigned = True
        break
      elif evt["is_america_action"] and evt["type"] == "Foul Committed":
        c_foul += 1
        assigned = True
        break
      elif (not evt["is_america_action"]) and evt["type"] == "Shot":
        c_shot += 1
        assigned = True
        break

    if not assigned:
      c_cont += 1

  print(f"   ✔️ Pérdidas totales evaluadas: {tot_turnovers:,}")
  print(
      f"   ✔️ Recuperaciones efectivas: {c_rec} ({c_rec / tot_turnovers * 100:.2f}%)"
  )
  print(
      f"   ✔️ Interrupciones por falta: {c_foul} ({c_foul / tot_turnovers * 100:.2f}%)"
  )
  print(
      f"   ✔️ Remates concedidos: {c_shot} ({c_shot / tot_turnovers * 100:.2f}%)"
  )
  print(
      f"   ✔️ Transición continuada: {c_cont}"
      f" ({c_cont / tot_turnovers * 100:.2f}%)"
  )

  # ------------------------------------------------------------------
  # 4. CÁLCULO DINÁMICO DE BALÓN PARADO (ABP) Y CORTES DE 4° PASE
  # ------------------------------------------------------------------
  print("\n4. Evaluando remates de Balón Parado (ABP) dinámicamente...")
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
    s_xg = shot["shot_statsbomb_xg"] if pd.notna(shot["shot_statsbomb_xg"]) else 0.0

    prev_passes = df_ev[
        (df_ev["match_id_clean"] == m_id)
        & (df_ev["type"] == "Pass")
        & (df_ev["play_pattern"] == shot["play_pattern"])
    ]
    prev_pass_times = prev_passes["minute"] * 60 + prev_passes["second"]

    valid_origin = prev_pass_times[
        (s_time - prev_pass_times >= 0) & (s_time - prev_pass_times <= 10.0)
    ]

    if len(valid_origin) <= 3:
      valid_abp_shots_cnt += 1
      valid_abp_xg_sum += s_xg
    else:
      reclassified_shots_cnt += 1
      reclassified_xg_sum += s_xg

  print(
      f"   ✔️ Remates totales etiquetados como ABP: {tot_abp_shots_cnt} (xG:"
      f" {tot_abp_xg_sum:.2f})"
  )
  print(
      f"   ✔️ Remates retenidos en ABP (<= 3 pases): {valid_abp_shots_cnt} (xG:"
      f" {valid_abp_xg_sum:.2f})"
  )
  print(
      f"   ✔️ Remates reclasificados a Juego Abierto (>= 4° pase):"
      f" {reclassified_shots_cnt} (xG: {reclassified_xg_sum:.2f})"
  )

  # ------------------------------------------------------------------
  # 5. GENERACIÓN AUTOMATIZADA Y DINÁMICA DE LOS ENTREGABLES
  # ------------------------------------------------------------------
  print("\n5. Exportando entregables oficiales con los datos calculados...")

  # A. JSON de Auditoría
  audit_file = PROCESSED_DIR / "audit_phase2_final.json"
  dynamic_audit_content = {
      "fase": "2.3 - Auditoría y Aceptación Metodológica Final",
      "version": "v1.0-CONSOLIDATED",
      "estatus": "APROBADO_100_PORCIENTO_CALCULADO",
      "ppda_fase_regular": {
          "partidos_evaluados": cnt_reg_matches,
          "partidos_denominador_cero": zero_denom_count,
          "pases_intentados_rival_x60": tot_pases_riv,
          "acciones_defensivas_america_x60": tot_def_actions,
          "ppda_media_partidos": round(mean_ppda_reg, 2),
          "ppda_mediana_partidos": round(median_ppda_reg, 2),
          "ppda_cociente_agregado": round(agg_ppda_reg, 2),
      },
      "field_tilt_fase_regular": {
          "field_tilt_media": round(mean_ft_reg, 2),
          "field_tilt_mediana": round(median_ft_reg, 2),
      },
      "pases_progresivos": {
          "universo_completados_totales": tot_completed,
          "pases_reinicio_excluidos": tot_restarts,
          "universo_juego_abierto": tot_open_play,
          "progresivos_base_30_15_10": prog_base_cnt,
          "pct_base": round(pct_prog_base, 2),
          "progresivos_estricta_35_20_15": prog_strict_cnt,
          "pct_estricta": round(pct_prog_strict, 2),
      },
      "transiciones_r10": {
          "total_perdidas_evaluadas": tot_turnovers,
          "recuperacion_efectiva": c_rec,
          "pct_recuperacion": round(c_rec / tot_turnovers * 100, 2),
          "interrupcion_falta": c_foul,
          "pct_falta": round(c_foul / tot_turnovers * 100, 2),
          "remate_concedido": c_shot,
          "pct_remate": round(c_shot / tot_turnovers * 100, 2),
          "transicion_continuada": c_cont,
          "pct_continuada": round(c_cont / tot_turnovers * 100, 2),
      },
      "balon_parado_abp": {
          "remates_totales_abp": tot_abp_shots_cnt,
          "xg_total_abp": round(tot_abp_xg_sum, 2),
          "remates_retenidos_le3_pases": valid_abp_shots_cnt,
          "xg_retenido": round(valid_abp_xg_sum, 2),
          "remates_reclasificados_juego_abierto": reclassified_shots_cnt,
          "xg_reclasificado": round(reclassified_xg_sum, 2),
      },
  }

  with open(audit_file, "w", encoding="utf-8") as f:
    json.dump(dynamic_audit_content, f, indent=4, ensure_ascii=False)

  # B. Documento Metodológico Markdown
  meta_md = PROCESSED_DIR / "metodologia_v1.0.md"
  with open(meta_md, "w", encoding="utf-8") as f:
    f.write(f"""# Documento de Metodología y Contrato Técnico (v1.0-CONSOLIDATED)
Proyecto: El Vuelo del Bicampeón (ISAC 2026)
*Generado automáticamente mediante cálculo dinámico de datos.*

## 1. Definición de Indicadores Tácticos

### A. Field Tilt ($FT_m$)
- **Fórmula:** (Pases completados América X>=80) / (Pases completados América X>=80 + Pases completados Rival X>=80) * 100
- **Universo:** {len(df_m)} partidos.
- **Resultados Fase Regular ({cnt_reg_matches} partidos):** Media = {mean_ft_reg:.2f}%, Mediana = {median_ft_reg:.2f}%.

### B. PPDA ($PPDA_m$)
- **Fórmula:** Pases intentados Rival (X<=60) / Acciones defensivas deduplicadas América (X>=60)
- **Acciones Defensivas:** Tackle, Intercepción, Falta cometida, Duelo defensivo y Bloqueo.
- **Universo Fase Regular:** {cnt_reg_matches} partidos ({zero_denom_count} partidos con denominador cero).
- **Valores Oficiales Calculados:**
  - Pases Rival X<=60 Totales: {tot_pases_riv:,} (Promedio: {tot_pases_riv/cnt_reg_matches:.2f} pases/partido)
  - Acciones Defensivas América X>=60 Totales: {tot_def_actions:,} (Promedio: {tot_def_actions/cnt_reg_matches:.2f} acciones/partido)
  - PPDA Media por Partido: {mean_ppda_reg:.2f}
  - PPDA Mediana por Partido: {median_ppda_reg:.2f}
  - PPDA Cociente Agregado: {agg_ppda_reg:.2f}

### C. Pases Progresivos
- **Pases Completados Totales:** {tot_completed:,}
- **Reinicios Excluidos:** {tot_restarts:,}
- **Universo Oficial de Juego Abierto:** {tot_open_play:,} pases completados.
- **Regla Base (30/15/10%):** {prog_base_cnt:,} pases ({pct_prog_base:.2f}%).
- **Regla Estricta (35/20/15%):** {prog_strict_cnt:,} pases ({pct_prog_strict:.2f}%).

### D. Transiciones Defensivas ($R_{{10}}$)
- **Pérdidas Evaluadas:** {tot_turnovers:,}.
- **Recuperación Efectiva:** {c_rec:,} ({c_rec/tot_turnovers*100:.2f}%).
- **Interrupción por Falta:** {c_foul:,} ({c_foul/tot_turnovers*100:.2f}%).
- **Remate Concedido:** {c_shot:,} ({c_shot/tot_turnovers*100:.2f}%).
- **Continuación / Sin Acción Inmediata:** {c_cont:,} ({c_cont/tot_turnovers*100:.2f}%).

### E. Balón Parado (ABP)
- **Remates Totales Etiquetados:** {tot_abp_shots_cnt} ({tot_abp_xg_sum:.2f} xG).
- **Remates Retenidos en ABP (<= 3 pases):** {valid_abp_shots_cnt} ({valid_abp_xg_sum:.2f} xG).
- **Remates Reclasificados (>= 4° pase):** {reclassified_shots_cnt} ({reclassified_xg_sum:.2f} xG).
""")

  print("\n==================================================================")
  print("✅ RECONCILIACIÓN Y CÁLCULO DINÁMICO FINALIZADO CON ÉXITO.")
  print("📦 Artefactos calculados directamente desde datos:")
  print(f"   1. {csv_out.name}")
  print(f"   2. {audit_file.name}")
  print(f"   3. {meta_md.name}")
  print("==================================================================")


if __name__ == "__main__":
  run_dynamic_reconciliation()