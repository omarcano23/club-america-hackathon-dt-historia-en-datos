"""
Paso 04: Análisis Contextual y Evolutivo (André Jardine)
Compara el rendimiento táctico por Temporada (2023/24 vs 2024/25) y Estado del Marcador.
"""

import sys
import json
from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

PROCESSED_DIR = ROOT / "data" / "processed"

def load_season_map(matches_index_path: Path) -> dict:
    """Extrae el mapeo match_id -> season_name."""
    with open(matches_index_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    df_matches = pd.DataFrame(data)
    
    if "season_name" in df_matches.columns:
        return dict(zip(df_matches["match_id"], df_matches["season_name"]))
    elif "season" in df_matches.columns:
        seasons = df_matches["season"].apply(lambda x: x.get("season_name") if isinstance(x, dict) else str(x))
        return dict(zip(df_matches["match_id"], seasons))
    elif "season_id_ref" in df_matches.columns:
        s_id_to_name = {281: "2023/2024", 317: "2024/2025"}
        return dict(zip(df_matches["match_id"], df_matches["season_id_ref"].map(s_id_to_name)))
    else:
        raise KeyError(f"No se encontró información de temporada en {matches_index_path}")

def main():
    print("=== PASO 04: ANÁLISIS EVOLUTIVO Y CONTEXTUAL ===")
    
    events_path = PROCESSED_DIR / "events_master.csv"
    matches_index_path = ROOT / "data" / "raw" / "jardine_matches_index.json"
    
    if not events_path.exists():
        sys.exit("Error: No se encontró 'events_master.csv'")
        
    print("Cargando datos de eventos e índice de partidos...")
    df_events = pd.read_csv(events_path, low_memory=False)
    
    # Mapear temporadas
    season_map = load_season_map(matches_index_path)
    df_events["season_name"] = df_events["match_id"].map(season_map)
    
    # 1. Comparación por Temporada
    print("\n--- 1. COMPARACIÓN POR TEMPORADA (EVOLUCIÓN) ---")
    seasons = df_events["season_name"].dropna().unique()
    
    season_results = []
    for s_name in sorted(seasons):
        s_events = df_events[df_events["season_name"] == s_name]
        
        s_shots = s_events[(s_events["type"] == "Shot") & (s_events["is_america_action"])]
        s_xg = s_shots["shot_statsbomb_xg"].sum()
        s_goals = len(s_shots[s_shots["shot_outcome"] == "Goal"])
        
        s_passes = s_events[(s_events["type"] == "Pass") & (s_events["is_america_action"]) & (s_events["pass_outcome"].isna())].copy()
        s_passes["prog_x"] = s_passes["end_location_x"] - s_passes["location_x"]
        prog_count = len(s_passes[s_passes["prog_x"] >= 12.0])
        
        ft_passes = s_events[(s_events["type"] == "Pass") & (s_events["location_x"] >= 80)]
        ft_ame = len(ft_passes[ft_passes["is_america_action"]])
        ft_pct = (ft_ame / len(ft_passes) * 100) if len(ft_passes) > 0 else 0
        
        opp_p = len(s_events[(s_events["type"] == "Pass") & (~s_events["is_america_action"]) & (s_events["location_x"] <= 60)])
        ame_def = len(s_events[(s_events["type"].isin(["Pressure", "Duel", "Interception", "Foul Committed", "Block"])) & (s_events["is_america_action"]) & (s_events["location_x"] >= 60)])
        ppda = opp_p / ame_def if ame_def > 0 else np.nan
        
        res = {
            "Temporada": s_name,
            "Partidos_Registrados": s_events["match_id"].nunique(),
            "xG_Total": round(s_xg, 2),
            "Goles_Anotados": s_goals,
            "Tiros_Totales": len(s_shots),
            "Pases_Progresivos": prog_count,
            "Field_Tilt_%": round(ft_pct, 1),
            "PPDA": round(ppda, 2)
        }
        season_results.append(res)
        
    df_season_comp = pd.DataFrame(season_results)
    print(df_season_comp.to_string(index=False))
    
    # 2. Análisis por Carril y Fase
    print("\n--- 2. ANÁLISIS DE AVANCE POR ZONA DE CAMPO ---")
    ame_passes = df_events[(df_events["type"] == "Pass") & (df_events["is_america_action"]) & (df_events["pass_outcome"].isna())]
    
    third_1 = len(ame_passes[ame_passes["location_x"] <= 40])
    third_2 = len(ame_passes[(ame_passes["location_x"] > 40) & (ame_passes["location_x"] <= 80)])
    third_3 = len(ame_passes[ame_passes["location_x"] > 80])
    total_p = len(ame_passes)
    
    print(f"Pases en Tercio Inicial (Salida):    {third_1} ({round(third_1/total_p*100, 1)}%)")
    print(f"Pases en Tercio Medio (Progresión): {third_2} ({round(third_2/total_p*100, 1)}%)")
    print(f"Pases en Tercio Final (Creación):   {third_3} ({round(third_3/total_p*100, 1)}%)")
    
    # Guardar en data/processed
    out_season_path = PROCESSED_DIR / "jardine_season_evolution.csv"
    df_season_comp.to_csv(out_season_path, index=False)
    print(f"\nReporte de evolución guardado en '{out_season_path.relative_to(ROOT)}'")

if __name__ == "__main__":
    main()