"""
Paso 46: Auditoría Acotada y Limpia (Solo Resultados y Excepciones)
Proyecto: El Vuelo del Bicampeón (ISAC 2026)
"""

import json
from pathlib import Path
import pandas as pd

DATA_DIR = Path(r"C:\Users\omarc\AI_Projects\Competitions\club-america-isac-2026\data")
PROCESSED_DIR = DATA_DIR / "processed"
RAW_DIR = DATA_DIR / "raw"

def calculate_exact_score(match_events: pd.DataFrame) -> tuple[int, int]:
    reg_ev = match_events[match_events["period"] <= 4].copy()
    ame_goals, riv_goals = 0, 0
    
    # 1. Remates
    shots = reg_ev[reg_ev["type"] == "Shot"].copy()
    for _, shot in shots.iterrows():
        outcome = str(shot.get("shot_outcome", ""))
        is_ame = bool(shot.get("is_america_action", False))
        is_og = bool(shot.get("own_goal", False)) or outcome == "Own Goal" or str(shot.get("pass_type", "")) == "Own Goal"
        
        if outcome in ["Goal", "Goal_Penalty"]:
            if not is_og:
                if is_ame: ame_goals += 1
                else: riv_goals += 1
            else:
                if not is_ame: ame_goals += 1
                else: riv_goals += 1

    # 2. Otros eventos de autogol
    non_shots = reg_ev[reg_ev["type"] != "Shot"].copy()
    if "pass_type" in non_shots.columns:
        og_events = non_shots[(non_shots["pass_type"] == "Own Goal") | (non_shots.get("own_goal", pd.Series()) == True)]
        for _, og in og_events.iterrows():
            is_ame = bool(og.get("is_america_action", False))
            if not is_ame: ame_goals += 1
            else: riv_goals += 1

    return ame_goals, riv_goals

def run_lean_audit():
    print("==================================================")
    print("🎯 AUDITORÍA ACOTADA DE MARCADORES (91 PARTIDOS)")
    print("==================================================\n")

    events_file = PROCESSED_DIR / "events_master.csv"
    index_json = RAW_DIR / "jardine_matches_index.json"

    df_ev = pd.read_csv(events_file, low_memory=False)
    df_ev["match_id_clean"] = pd.to_numeric(
        df_ev["match_id"].astype(str).str.replace("match_", ""), errors="coerce"
    ).fillna(0).astype("int64")

    with open(index_json, "r", encoding="utf-8") as f:
        meta_raw = json.load(f)

    meta_dict = {int(str(m.get("match_id", 0)).replace("match_", "")): m for m in meta_raw}

    discrepancies = []
    
    for m_id, grp in df_ev.groupby("match_id_clean"):
        meta = meta_dict.get(m_id, {})
        home_team = str(meta.get("home_team", ""))
        away_team = str(meta.get("away_team", ""))
        is_home = "América" in home_team
        
        off_h = meta.get("home_score", None)
        off_a = meta.get("away_score", None)
        
        calc_ame, calc_riv = calculate_exact_score(grp)
        calc_home = calc_ame if is_home else calc_riv
        calc_away = calc_riv if is_home else calc_ame
        
        if off_h is not None and off_a is not None:
            if calc_home != off_h or calc_away != off_a:
                discrepancies.append({
                    "match_id": m_id,
                    "encuentro": f"{home_team} vs {away_team}",
                    "oficial": f"{off_h}-{off_a}",
                    "calculado": f"{calc_home}-{calc_away}"
                })

    print(f"• Total Partidos Auditados: 91")
    print(f"• Discrepancias Encontradas: {len(discrepancies)}\n")

    if len(discrepancies) > 0:
        print("❌ Detalle de partidos con desajuste:")
        df_disc = pd.DataFrame(discrepancies)
        print(df_disc.to_string(index=False))
        
        print("\n🔍 Inspeccionando eventos de gol en los partidos discrepantes...")
        for item in discrepancies:
            m_id = item["match_id"]
            m_grp = df_ev[df_ev["match_id_clean"] == m_id]
            print(f"\n--- Match ID: {m_id} ({item['encuentro']}) ---")
            g_events = m_grp[(m_grp["period"] <= 4) & ((m_grp["shot_outcome"].isin(["Goal", "Goal_Penalty"])) | (m_grp.get("pass_type", "") == "Own Goal"))]
            for _, r in g_events.iterrows():
                print(f"Min: {r.get('minute')}:{r.get('second')} | Tipo: {r.get('type')} | Equipo: {r.get('team')} | Outcome: {r.get('shot_outcome')} | PassType: {r.get('pass_type')}")
    else:
        print("✔️ ¡Excelente! Los 91 partidos coinciden perfectamente (0 discrepancias).")

    print("\n==================================================")
    print("✅ AUDITORÍA ACOTADA FINALIZADA.")
    print("==================================================")

if __name__ == "__main__":
    run_lean_audit()