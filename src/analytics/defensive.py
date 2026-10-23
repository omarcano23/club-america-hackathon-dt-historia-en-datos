"""
Módulo de Análisis Defensivo - André Jardine (Club América)
Calcula PPDA, Field Tilt y zonas de recuperación defensiva.
"""

import pandas as pd
import numpy as np

def calculate_ppda(df_events):
    """
    Calcula el PPDA (Passes Allowed Per Defensive Action).
    Definición: Pases hechos por los rivales en sus primeros 60m / 
                Acciones defensivas del América en esos mismos 60m.
    Un PPDA menor a 10 indica una presión intensa e agresiva alta.
    """
    # Pases del rival en su propio campo (X <= 60 en perspectiva del rival -> X >= 60 para América)
    opponent_passes = df_events[
        (df_events["type"] == "Pass") & 
        (~df_events["is_america_action"]) & 
        (df_events["location_x"] <= 60)
    ]
    
    # Acciones defensivas del América en campo rival (X >= 60)
    defensive_types = ["Pressure", "Duel", "Interception", "Foul Committed", "Block"]
    america_def_actions = df_events[
        (df_events["type"].isin(defensive_types)) & 
        (df_events["is_america_action"]) & 
        (df_events["location_x"] >= 60)
    ]
    
    num_opp_passes = len(opponent_passes)
    num_def_actions = len(america_def_actions)
    
    ppda = num_opp_passes / num_def_actions if num_def_actions > 0 else np.nan
    return round(ppda, 2)

def calculate_field_tilt(df_events):
    """
    Calcula el Field Tilt (Dominio territorial en último tercio).
    Definición: Pases del América en último tercio (X >= 80) / 
                Pases totales en último tercio de ambos equipos.
    """
    final_third_passes = df_events[
        (df_events["type"] == "Pass") & 
        (df_events["location_x"] >= 80)
    ]
    
    america_ft_passes = len(final_third_passes[final_third_passes["is_america_action"]])
    total_ft_passes = len(final_third_passes)
    
    field_tilt = (america_ft_passes / total_ft_passes * 100) if total_ft_passes > 0 else 0
    return round(field_tilt, 2)

def calculate_high_recoveries(df_events):
    """
    Identifica recuperaciones de balón en campo rival (X >= 60).
    """
    recovery_types = ["Ball Recovery", "Interception"]
    recoveries = df_events[
        (df_events["type"].isin(recovery_types)) & 
        (df_events["is_america_action"])
    ]
    
    high_rec = recoveries[recoveries["location_x"] >= 60]
    return {
        "total_recoveries": len(recoveries),
        "high_recoveries": len(high_rec),
        "high_recovery_pct": round(len(high_rec) / len(recoveries) * 100, 2) if len(recoveries) > 0 else 0
    }