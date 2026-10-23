"""
Paso 02: Consolidación a Capa Processed - Proyecto Club América ISAC 2026
Lee los JSONs individuales de data/raw/matches/ y genera los datasets consolidados en data/processed/.
Maneja de forma segura el bloqueo de DLLs de Parquet usando exportación CSV directa.
"""

import json
import sys
from pathlib import Path
import pandas as pd
import numpy as np

# Rutas del proyecto
ROOT = Path(__file__).resolve().parents[1]
RAW_MATCHES_DIR = ROOT / "data" / "raw" / "matches"
PROCESSED_DIR = ROOT / "data" / "processed"

def load_json(path: Path):
    """Carga un archivo JSON si existe, retorna None si no."""
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"   [!] Error al leer {path.name}: {e}")
        return None

def process_events(events_raw, match_id):
    """Procesa y limpia la lista de eventos brutos de un partido."""
    parsed_events = []
    
    for ev in events_raw:
        # Ubicación X, Y de la acción
        loc = ev.get("location")
        x_loc = loc[0] if isinstance(loc, list) and len(loc) >= 2 else np.nan
        y_loc = loc[1] if isinstance(loc, list) and len(loc) >= 2 else np.nan
        
        # Ubicación fin de pase o tiro
        pass_end = ev.get("pass_end_location") or ev.get("carry_end_location") or ev.get("shot_end_location")
        end_x = pass_end[0] if isinstance(pass_end, list) and len(pass_end) >= 2 else np.nan
        end_y = pass_end[1] if isinstance(pass_end, list) and len(pass_end) >= 2 else np.nan
        
        # Táctica inicial
        tactics = ev.get("tactics", {})
        formation = tactics.get("formation") if isinstance(tactics, dict) else np.nan
        
        parsed_ev = {
            "match_id": match_id,
            "event_id": str(ev.get("id")) if ev.get("id") else None,
            "index": ev.get("index"),
            "period": ev.get("period"),
            "timestamp": str(ev.get("timestamp")),
            "minute": ev.get("minute"),
            "second": ev.get("second"),
            "type": str(ev.get("type")) if ev.get("type") else None,
            "possession": ev.get("possession"),
            "possession_team": str(ev.get("possession_team")) if ev.get("possession_team") else None,
            "team": str(ev.get("team")) if ev.get("team") else None,
            "player": str(ev.get("player")) if ev.get("player") else None,
            "player_id": ev.get("player_id"),
            "position": str(ev.get("position")) if ev.get("position") else None,
            "location_x": float(x_loc) if not np.isnan(x_loc) else np.nan,
            "location_y": float(y_loc) if not np.isnan(y_loc) else np.nan,
            "end_location_x": float(end_x) if not np.isnan(end_x) else np.nan,
            "end_location_y": float(end_y) if not np.isnan(end_y) else np.nan,
            "duration": float(ev.get("duration", 0.0) or 0.0),
            "under_pressure": bool(ev.get("under_pressure", False)),
            "counterpress": bool(ev.get("counterpress", False)),
            "play_pattern": str(ev.get("play_pattern")) if ev.get("play_pattern") else None,
            "pass_recipient": str(ev.get("pass_recipient")) if ev.get("pass_recipient") else None,
            "pass_length": float(ev.get("pass_length")) if ev.get("pass_length") is not None else np.nan,
            "pass_angle": float(ev.get("pass_angle")) if ev.get("pass_angle") is not None else np.nan,
            "pass_outcome": str(ev.get("pass_outcome")) if ev.get("pass_outcome") else None,
            "shot_statsbomb_xg": float(ev.get("shot_statsbomb_xg")) if ev.get("shot_statsbomb_xg") is not None else np.nan,
            "shot_outcome": str(ev.get("shot_outcome")) if ev.get("shot_outcome") else None,
            "obv_total_net": float(ev.get("obv_total_net")) if ev.get("obv_total_net") is not None else np.nan,
            "formation": float(formation) if not np.isnan(formation) else np.nan
        }
        parsed_events.append(parsed_ev)
        
    return pd.DataFrame(parsed_events)

def process_frames_360(frames_raw, match_id):
    """Procesa y limpia los congelamientos 360 de un partido."""
    parsed_frames = []
    
    for frame in frames_raw:
        event_id = frame.get("id")
        loc = frame.get("location")
        x_loc = loc[0] if isinstance(loc, list) and len(loc) >= 2 else np.nan
        y_loc = loc[1] if isinstance(loc, list) and len(loc) >= 2 else np.nan
        
        parsed_f = {
            "match_id": match_id,
            "event_id": str(event_id) if event_id else None,
            "teammate": bool(frame.get("teammate", False)),
            "actor": bool(frame.get("actor", False)),
            "keeper": bool(frame.get("keeper", False)),
            "player_x": float(x_loc) if not np.isnan(x_loc) else np.nan,
            "player_y": float(y_loc) if not np.isnan(y_loc) else np.nan,
            "distance_from_edge": float(frame.get("distance_from_edge_of_visible_area")) if frame.get("distance_from_edge_of_visible_area") is not None else np.nan
        }
        parsed_frames.append(parsed_f)
        
    return pd.DataFrame(parsed_frames)

def build_possessions_summary(events_df):
    """Agrupa eventos para construir el resumen nivel Posesión."""
    if events_df.empty:
        return pd.DataFrame()
        
    poss_rows = []
    grouped = events_df.groupby(["match_id", "possession"])
    
    for (m_id, poss_id), group in grouped:
        first_ev = group.iloc[0]
        last_ev = group.iloc[-1]
        
        passes = group[group["type"] == "Pass"]
        shots = group[group["type"] == "Shot"]
        
        poss_data = {
            "match_id": m_id,
            "possession_id": poss_id,
            "possession_team": first_ev["possession_team"],
            "start_minute": first_ev["minute"],
            "start_second": first_ev["second"],
            "end_minute": last_ev["minute"],
            "end_second": last_ev["second"],
            "event_count": len(group),
            "pass_count": len(passes),
            "shot_count": len(shots),
            "total_xg": group["shot_statsbomb_xg"].sum(min_count=1),
            "start_x": first_ev["location_x"],
            "start_y": first_ev["location_y"],
            "end_x": last_ev["location_x"],
            "end_y": last_ev["location_y"],
            "play_pattern": first_ev["play_pattern"],
            "has_shot": len(shots) > 0
        }
        poss_rows.append(poss_data)
        
    return pd.DataFrame(poss_rows)

def save_dataframe_safe(df: pd.DataFrame, base_path: Path):
    """
    Intenta guardar en Parquet; si la política de seguridad del sistema
    bloquea la DLL de pyarrow/fastparquet, guarda en CSV y CSV comprimido.
    """
    csv_path = base_path.with_suffix(".csv")
    df.to_csv(csv_path, index=False)
    print(f"  -> Guardado CSV: {len(df)} registros en '{csv_path.name}'.")
    
    # Probar si Parquet está disponible y permitido por el SO
    try:
        parquet_path = base_path.with_suffix(".parquet")
        df.to_parquet(parquet_path, index=False, engine="fastparquet")
        print(f"  -> Guardado Parquet: '{parquet_path.name}'.")
    except Exception as e:
        print(f"  [*] Parquet no disponible por política de seguridad del sistema ({type(e).__name__}). Se usará únicamente CSV.")

def main():
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    
    match_folders = [f for f in RAW_MATCHES_DIR.iterdir() if f.is_dir()]
    print(f"=== PROCESANDO {len(match_folders)} PARTIDOS A CAPA PROCESSED ===")
    
    all_events = []
    all_frames = []
    
    for idx, match_folder in enumerate(match_folders, start=1):
        match_id = int(match_folder.name)
        print(f"[{idx}/{len(match_folders)}] Procesando partido {match_id}...")
        
        # 1. Eventos
        events_raw = load_json(match_folder / "events.json")
        if events_raw:
            df_ev = process_events(events_raw, match_id)
            all_events.append(df_ev)
            
        # 2. Frames 360
        frames_raw = load_json(match_folder / "frames_360.json")
        if frames_raw:
            df_fr = process_frames_360(frames_raw, match_id)
            all_frames.append(df_fr)
            
    # Consolidación final
    print("\nConsolidando tablas maestras...")
    
    if all_events:
        master_events_df = pd.concat(all_events, ignore_index=True)
        
        # Identificar si es acción del América
        master_events_df["is_america_possession"] = master_events_df["possession_team"].str.contains("América|America", na=False)
        master_events_df["is_america_action"] = master_events_df["team"].str.contains("América|America", na=False)
        
        # Guardar Eventos Master
        save_dataframe_safe(master_events_df, PROCESSED_DIR / "events_master")
        
        # Guardar Posesiones
        master_possessions_df = build_possessions_summary(master_events_df)
        save_dataframe_safe(master_possessions_df, PROCESSED_DIR / "possessions_master")

    if all_frames:
        master_frames_df = pd.concat(all_frames, ignore_index=True)
        save_dataframe_safe(master_frames_df, PROCESSED_DIR / "frames_360_master")

    print("\nProceso completado con éxito. Capa Processed lista para análisis táctico.")

if __name__ == "__main__":
    main()