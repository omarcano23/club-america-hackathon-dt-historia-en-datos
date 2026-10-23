"""
Paso 03: Desglose por Fase y Auditoría de Integridad de Campos (G2, G3, G4)
Fase 1.1 - ISAC 2026
"""

import json
from pathlib import Path
import pandas as pd

DATA_DIR = Path(r"C:\Users\omarc\AI_Projects\Competitions\club-america-isac-2026\data")

def audit_stages_and_integrity():
    print("==================================================================")
    print("🔍 AUDITANDO FASES Y COBERTURA DE EVENTOS (PASOS 3 Y 4)")
    print("==================================================================\n")

    raw_dir = DATA_DIR / "raw"
    processed_dir = DATA_DIR / "processed"

    # 1. Cargar metadatos
    index_file = raw_dir / "jardine_matches_index.json"
    with open(index_file, "r", encoding="utf-8") as f:
        matches_data = json.load(f)

    df_matches = pd.DataFrame(matches_data)

    # Identificar columna de fase/etapa en los metadatos
    stage_col = None
    for col in ['competition_stage', 'stage_name', 'stage', 'type']:
        if col in df_matches.columns:
            stage_col = col
            break
            
    print(f"📋 Desglose detallado por Temporada y Fase/Etapa ('{stage_col}'):")
    print("-" * 65)
    if stage_col:
        stage_summary = df_matches.groupby(['season', stage_col]).size().reset_index(name='partidos')
        print(stage_summary.to_string(index=False))
    else:
        print("Muestra de columnas disponibles en los metadatos:")
        print(df_matches.columns.tolist())

    print("\n------------------------------------------------------------------")
    print("🧪 AUDITANDO CAMPOS E INTEGRIDAD EN events_master.csv")
    print("------------------------------------------------------------------")

    events_file = processed_dir / "events_master.csv"
    if events_file.exists():
        # Leemos muestra de columnas y tipos de datos
        df_ev_sample = pd.read_csv(events_file, nrows=1000, low_memory=False)
        print(f"Total de columnas en events_master.csv: {len(df_ev_sample.columns)}")
        
        # Verificar presencia de campos críticos
        critical_fields = ['match_id', 'event_id', 'possession_id', 'type', 'team', 'player', 'location', 'pass_end_location', 'shot_statsbomb_xg', 'under_pressure']
        found_fields = [f for f in critical_fields if f in df_ev_sample.columns]
        missing_fields = [f for f in critical_fields if f not in df_ev_sample.columns]
        
        print(f"✔️ Campos críticos presentes ({len(found_fields)}): {found_fields}")
        if missing_fields:
            print(f"⚠️ Campos críticos NO encontrados de forma directa: {missing_fields}")

    print("\n------------------------------------------------------------------")
    print("📐 AUDITANDO COBERTURA REAL EN frames_360_master.csv")
    print("------------------------------------------------------------------")

    frames_file = processed_dir / "frames_360_master.csv"
    if frames_file.exists():
        df_360_sample = pd.read_csv(frames_file, nrows=1000, low_memory=False)
        print(f"Total de columnas en frames_360_master.csv: {len(df_360_sample.columns)}")
        print(f"Columnas 360 encontradas: {list(df_360_sample.columns)}")

if __name__ == "__main__":
    audit_stages_and_integrity()