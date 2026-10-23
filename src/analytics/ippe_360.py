"""
Módulo Métrica Propia 360: Índice de Progresión bajo Presión Estructural (IPPE)
Combina events_master con frames_360_master para evaluar la superación de bloques defensivos.
"""

import pandas as pd
import numpy as np

def calculate_ippe_metric(df_events, df_frames):
    """
    Calcula el IPPE del Club América.
    Evalúa pases completados en los que la imagen 360 detecta 3+ rivales en zona.
    """
    # 1. Pases completados del América
    passes = df_events[
        (df_events["type"] == "Pass") & 
        (df_events["is_america_action"]) & 
        (df_events["pass_outcome"].isna())
    ].copy()
    
    # Progreso en X (hacia meta rival)
    passes["progression_x"] = passes["end_location_x"] - passes["location_x"]
    progressive_passes = passes[passes["progression_x"] >= 10.0]
    
    if progressive_passes.empty or df_frames.empty:
        return {"total_progressive": 0, "ippe_successes": 0, "ippe_index_%": 0.0}
        
    # 2. Filtrar frames 360 para rivales (teammate == False)
    opponents_360 = df_frames[df_frames["teammate"] == False]
    
    # Contar rivales por cada congelamiento/evento
    opp_counts = opponents_360.groupby("event_id").size().reset_index(name="num_opponents_visible")
    
    # 3. Unir eventos de pase con el conteo 360
    merged = pd.merge(progressive_passes, opp_counts, on="event_id", how="inner")
    
    # Condición de Presión Estructural (3 o más rivales en la toma 360)
    high_pressure_passes = merged[merged["num_opponents_visible"] >= 3]
    
    total_prog = len(merged)
    ippe_count = len(high_pressure_passes)
    ippe_index = (ippe_count / total_prog * 100) if total_prog > 0 else 0.0
    
    return {
        "total_progressive_360_events": total_prog,
        "ippe_high_pressure_bypasses": ippe_count,
        "ippe_index_%": round(ippe_index, 2),
        "avg_opponents_bypassed": round(merged["num_opponents_visible"].mean(), 2) if not merged.empty else 0.0
    }