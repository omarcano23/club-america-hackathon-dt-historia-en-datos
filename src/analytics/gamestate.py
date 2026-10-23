"""
Módulo de Análisis de Marcador (Gamestate) - Club América
Calcula métricas tácticas segmentadas según el marcador puntual (Ganando, Empatando, Perdiendo).
"""

import pandas as pd
import numpy as np

def calculate_gamestate_metrics(df_events):
    """
    Rastrea el marcador en tiempo real por partido y compara el comportamiento.
    """
    df = df_events.sort_values(["match_id", "period", "minute", "second", "index"]).copy()
    
    # Identificar goles
    df["is_goal"] = (df["type"] == "Shot") & (df["shot_outcome"] == "Goal")
    df["america_goal"] = df["is_goal"] & df["is_america_action"]
    df["opponent_goal"] = df["is_goal"] & (~df["is_america_action"])
    
    # Marcador acumulado por partido
    df["cum_america_goals"] = df.groupby("match_id")["america_goal"].cumsum()
    df["cum_opponent_goals"] = df.groupby("match_id")["opponent_goal"].cumsum()
    
    # El marcador durante la jugada es el acumulado ANTES del gol
    df["score_diff"] = (df["cum_america_goals"] - df["america_goal"]) - (df["cum_opponent_goals"] - df["opponent_goal"])
    
    def assign_gamestate(diff):
        if diff > 0:
            return "Ganando"
        elif diff < 0:
            return "Perdiendo"
        else:
            return "Empatando"
            
    df["gamestate"] = df["score_diff"].apply(assign_gamestate)
    
    results = []
    for gs, group in df.groupby("gamestate"):
        total_events = len(group)
        ft_passes = group[(group["type"] == "Pass") & (group["location_x"] >= 80)]
        ft_ame = len(ft_passes[ft_passes["is_america_action"]])
        ft_pct = (ft_ame / len(ft_passes) * 100) if len(ft_passes) > 0 else 0
        
        # PPDA por marcador
        opp_p = len(group[(group["type"] == "Pass") & (~group["is_america_action"]) & (group["location_x"] <= 60)])
        ame_def = len(group[(group["type"].isin(["Pressure", "Duel", "Interception", "Foul Committed", "Block"])) & (group["is_america_action"]) & (group["location_x"] >= 60)])
        ppda = opp_p / ame_def if ame_def > 0 else np.nan
        
        results.append({
            "Gamestate": gs,
            "Eventos_Totales": total_events,
            "Field_Tilt_%": round(ft_pct, 1),
            "PPDA": round(ppda, 2)
        })
        
    return pd.DataFrame(results)