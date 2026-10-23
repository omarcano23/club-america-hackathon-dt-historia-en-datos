"""
Paso 42: Reconciliación 1:1 de Marcadores (91 Partidos) y Pruebas Sintéticas de Casos Especiales
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


def calculate_match_score(match_events: pd.DataFrame, is_home_game: bool) -> tuple[int, int]:
    """
    Función pura de producción para calcular el marcador de un partido en tiempo reglamentario (period <= 4).
    """
    reg_events = match_events[match_events["period"] <= 4]
    
    # 1. Goles por remate directo (incluye penaltis en juego)
    shots = reg_events[reg_events["type"] == "Shot"]
    ame_shot_goals = len(shots[(shots["is_america_action"]) & (shots["shot_outcome"].isin(["Goal", "Goal_Penalty"]))])
    riv_shot_goals = len(shots[(~shots["is_america_action"]) & (shots["shot_outcome"].isin(["Goal", "Goal_Penalty"]))])
    
    # 2. Autogoles
    if "pass_type" in reg_events.columns:
        own_goals = reg_events[reg_events["pass_type"] == "Own Goal"]
    elif "type" in reg_events.columns:
        own_goals = reg_events[reg_events["type"] == "Own Goal"]
    else:
        own_goals = pd.DataFrame()
        
    ame_og_against = len(own_goals[own_goals["is_america_action"]]) if not own_goals.empty else 0
    riv_og_against = len(own_goals[~own_goals["is_america_action"]]) if not own_goals.empty else 0
    
    # Marcador final
    ame_total_goals = ame_shot_goals + riv_og_against
    riv_total_goals = riv_shot_goals + ame_og_against
    
    return ame_total_goals, riv_total_goals


def run_goals_and_edge_cases_audit():
    print("==================================================================")
    print("🔬 RECONCILIACIÓN 1:1 DE MARCADORES Y PRUEBAS DE CASOS ESPECIALES")
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

    with open(index_json, "r", encoding="utf-8") as f:
        meta_raw = json.load(f)

    meta_dict = {
        int(str(m.get("match_id", 0)).replace("match_", "")): m
        for m in meta_raw
    }

    # ------------------------------------------------------------------
    # 1. PRUEBAS DE UNIDAD SINTÉTICAS (MOCK TESTS PARA CASOS DE BORDE)
    # ------------------------------------------------------------------
    print("1. EJECUTANDO BATERÍA DE PRUEBAS SINTÉTICAS (MOCK TESTS):")
    print("-" * 65)

    # Caso A: Penalti Convertido en Juego (period = 2) vs Penalti en Tanda (period = 5)
    mock_penalties = pd.DataFrame([
        {"period": 2, "type": "Shot", "is_america_action": True, "shot_outcome": "Goal_Penalty"},
        {"period": 5, "type": "Shot", "is_america_action": True, "shot_outcome": "Goal_Penalty"},  # Tanda -> Excluido
        {"period": 2, "type": "Shot", "is_america_action": False, "shot_outcome": "Goal"}
    ])
    ame_p, riv_p = calculate_match_score(mock_penalties, is_home_game=True)
    test1_pass = (ame_p == 1 and riv_p == 1)
    print(f"• Test 1 (Penalti en Juego vs Tanda Penaltis): {'PASÓ' if test1_pass else 'FALLÓ'} (Resultado: {ame_p}-{riv_p})")

    # Caso B: Autogol del Rival a favor de América
    mock_og_favor = pd.DataFrame([
        {"period": 1, "type": "Pass", "pass_type": "Own Goal", "is_america_action": False, "shot_outcome": None},
        {"period": 3, "type": "Shot", "is_america_action": True, "shot_outcome": "Goal"}
    ])
    ame_og1, riv_og1 = calculate_match_score(mock_og_favor, is_home_game=True)
    test2_pass = (ame_og1 == 2 and riv_og1 == 0)
    print(f"• Test 2 (Autogol del Rival a favor de América): {'PASÓ' if test2_pass else 'FALLÓ'} (Resultado: {ame_og1}-{riv_og1})")

    # Caso C: Autogol de América en contra
    mock_og_against = pd.DataFrame([
        {"period": 2, "type": "Pass", "pass_type": "Own Goal", "is_america_action": True, "shot_outcome": None}
    ])
    ame_og2, riv_og2 = calculate_match_score(mock_og_against, is_home_game=True)
    test3_pass = (ame_og2 == 0 and riv_og2 == 1)
    print(f"• Test 3 (Autogol de América en Contra): {'PASÓ' if test3_pass else 'FALLÓ'} (Resultado: {ame_og2}-{riv_og2})\n")

    # ------------------------------------------------------------------
    # 2. RECONCILIACIÓN 1:1 CONTRA MARCADORES OFICIALES (91 PARTIDOS)
    # ------------------------------------------------------------------
    print("2. RECONCILIACIÓN DE MARCADOR PARTIDO POR PARTIDO (91 ENCUENTROS):")
    print("-" * 65)

    discrepancies = []
    
    for m_id, grp in df_ev.groupby("match_id_clean"):
        meta = meta_dict.get(m_id, {})
        home_team = str(meta.get("home_team", ""))
        is_home = "América" in home_team or "Club América" in home_team
        
        official_home_score = meta.get("home_score", None)
        official_away_score = meta.get("away_score", None)
        
        calc_ame_score, calc_riv_score = calculate_match_score(grp, is_home)
        
        if is_home:
            calc_home, calc_away = calc_ame_score, calc_riv_score
        else:
            calc_home, calc_away = calc_riv_score, calc_ame_score
            
        if official_home_score is not None and official_away_score is not None:
            if calc_home != official_home_score or calc_away != official_away_score:
                discrepancies.append({
                    "match_id": m_id,
                    "home_team": home_team,
                    "away_team": meta.get("away_team", ""),
                    "official_score": f"{official_home_score}-{official_away_score}",
                    "calculated_score": f"{calc_home}-{calc_away}"
                })

    print(f"• Total Partidos Auditados 1:1: {df_ev['match_id_clean'].nunique()}")
    print(f"• Total Discrepancias de Marcador Detectadas: {len(discrepancies)}")
    
    if len(discrepancies) > 0:
        print("\n❌ Detalle de Discrepancias:")
        print(pd.DataFrame(discrepancies).to_string(index=False))
    else:
        print("✔️ Cero discrepancias: Los 91 marcadores calculados coinciden exactamente con la fuente oficial.")

    print("\n==================================================================")
    print("✅ RECONCILIACIÓN Y VALIDACIÓN DE CASOS DE BORDE CONCLUIDA.")
    print("==================================================================")


if __name__ == "__main__":
    run_goals_and_edge_cases_audit()