"""
Módulo de Análisis Ofensivo - André Jardine (Club América)
Calcula métricas de progresión, construcción y generación de ocasiones.
"""

import pandas as pd
import numpy as np

def calculate_progressive_passes(df_events, min_progression_meters=10.0):
    """
    Identifica pases progresivos del Club América.
    Definición: Pases en campo propio que avanzan >= 15m hacia meta rival,
    o en campo rival que avanzan >= 10m hacia meta rival.
    """
    passes = df_events[(df_events["type"] == "Pass") & (df_events["is_america_action"])].copy()
    
    # Filtrar pases incompletos o fuera
    passes = passes[passes["pass_outcome"].isna()]
    
    # Calcular distancia de progresión en eje X (coordenadas StatsBomb: 0 a 120m)
    passes["progression_x"] = passes["end_location_x"] - passes["location_x"]
    
    # Criterio de Pase Progresivo
    is_in_own_half = passes["location_x"] < 60
    cond_own = is_in_own_half & (passes["progression_x"] >= 15.0)
    cond_opp = (~is_in_own_half) & (passes["progression_x"] >= min_progression_meters)
    
    passes["is_progressive"] = cond_own | cond_opp
    return passes

def calculate_build_up_patterns(df_events):
    """
    Calcula la proporción de pases de salida por carril (Izquierdo, Centro, Derecho)
    en el primer tercio del campo (X <= 40).
    """
    build_up = df_events[
        (df_events["type"] == "Pass") & 
        (df_events["is_america_action"]) & 
        (df_events["location_x"] <= 40)
    ].copy()
    
    # StatsBomb Y va de 0 a 80 (0=Arriba/Izquierda, 80=Abajo/Derecha)
    def assign_lane(y):
        if y < 26.6:
            return "Izquierdo"
        elif y <= 53.3:
            return "Central"
        else:
            return "Derecho"
            
    build_up["lane"] = build_up["location_y"].apply(assign_lane)
    lane_distribution = build_up["lane"].value_counts(normalize=True) * 100
    return lane_distribution.to_dict()

def calculate_xg_summary(df_events):
    """
    Resume el xG total, tiros a gol y xG por tiro del Club América.
    """
    shots = df_events[(df_events["type"] == "Shot") & (df_events["is_america_action"])].copy()
    
    total_xg = shots["shot_statsbomb_xg"].sum()
    total_shots = len(shots)
    goals = len(shots[shots["shot_outcome"] == "Goal"])
    xg_per_shot = total_xg / total_shots if total_shots > 0 else 0
    
    return {
        "total_shots": total_shots,
        "goals": goals,
        "total_xg": round(total_xg, 2),
        "xg_per_shot": round(xg_per_shot, 3)
    }