"""
Módulo de Redes de Pases (Passing Networks) - Club América
Calcula la posición media de los 11 titulares y la matriz de pases entre ellos.
"""

import pandas as pd
import numpy as np

def calculate_passing_network(df_events, match_id=None):
    """
    Calcula la posición media y conexiones entre titulares del América.
    Si match_id es None, procesa el primer partido disponible.
    """
    if match_id is None:
        match_id = df_events["match_id"].iloc[0]
        
    match_events = df_events[(df_events["match_id"] == match_id) & (df_events["is_america_action"])].copy()
    
    # Identificar pases completados con jugador y receptor
    passes = match_events[
        (match_events["type"] == "Pass") & 
        (match_events["pass_outcome"].isna()) &
        (match_events["player"].notna()) &
        (match_events["pass_recipient"].notna())
    ]
    
    # Calcular ubicación promedio por jugador
    locations = passes.groupby("player").agg(
        x_mean=("location_x", "mean"),
        y_mean=("location_y", "mean"),
        count=("event_id", "count")
    ).reset_index()
    
    # Filtrar solo los 11 más participativos (titulares)
    top11 = locations.nlargest(11, "count")["player"].tolist()
    locations_11 = locations[locations["player"].isin(top11)].copy()
    
    # Matriz de conexiones entre los 11
    passes_11 = passes[(passes["player"].isin(top11)) & (passes["pass_recipient"].isin(top11))]
    connections = passes_11.groupby(["player", "pass_recipient"]).size().reset_index(name="pass_count")
    
    return {
        "match_id": match_id,
        "nodes": locations_11,
        "edges": connections
    }