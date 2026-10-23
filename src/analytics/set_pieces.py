"""
Módulo de Balón Parado (ABP) - Club América
Analiza córners, tiros libres y patrones de remate tras ABP.
"""

import pandas as pd
import numpy as np

def calculate_set_piece_metrics(df_events):
    """
    Resume la efectividad de las jugadas a balón parado ofensivas y defensivas.
    """
    # Córners y Tiros Libres Ofensivos del América
    corners_off = df_events[
        (df_events["play_pattern"] == "From Corner") & 
        (df_events["is_america_action"])
    ]
    
    free_kicks_off = df_events[
        (df_events["play_pattern"].isin(["From Free Kick", "From Throw In"])) & 
        (df_events["is_america_action"])
    ]
    
    # Remates derivados de ABP
    shots_abp = df_events[
        (df_events["type"] == "Shot") & 
        (df_events["is_america_action"]) & 
        (df_events["play_pattern"].isin(["From Corner", "From Free Kick"]))
    ]
    
    total_xg_abp = shots_abp["shot_statsbomb_xg"].sum()
    goals_abp = len(shots_abp[shots_abp["shot_outcome"] == "Goal"])
    
    return {
        "total_corners": len(corners_off[corners_off["type"] == "Pass"]),
        "total_free_kicks": len(free_kicks_off[free_kicks_off["type"] == "Pass"]),
        "shots_from_abp": len(shots_abp),
        "goals_from_abp": goals_abp,
        "xg_from_abp": round(total_xg_abp, 2)
    }