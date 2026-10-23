"""
Paso 06: Reconciliación Forense de Partidos e Identificación de Fases
Fase 1.1 - ISAC 2026 (El Vuelo del Bicampeón)
"""

import json
from pathlib import Path
import pandas as pd

DATA_DIR = Path(r"C:\Users\omarc\AI_Projects\Competitions\club-america-isac-2026\data")

def reconcile_match_ids():
    print("==================================================================")
    print("🔬 RECONCILIACIÓN FORENSE DE MATCH_IDs Y CLASIFICACIÓN DE FASES")
    print("==================================================================\n")

    raw_dir = DATA_DIR / "raw"
    processed_dir = DATA_DIR / "processed"

    # 1. Cargar el índice oficial de Jardine (91 partidos)
    index_file = raw_dir / "jardine_matches_index.json"
    with open(index_file, "r", encoding="utf-8") as f:
        jardine_index = json.load(f)

    df_jardine = pd.DataFrame(jardine_index)
    jardine_ids = set(df_jardine['match_id'].unique())
    print(f"1. IDs en jardine_matches_index.json: {len(jardine_ids)} partidos")

    # 2. Cargar IDs del catálogo general de Liga MX si existe
    matches_mx_csv = raw_dir / "matches_liga_mx.csv"
    mx_ids = set()
    if matches_mx_csv.exists():
        try:
            df_mx = pd.read_csv(matches_mx_csv, low_memory=False)
            if 'match_id' in df_mx.columns:
                mx_ids = set(df_mx['match_id'].unique())
                print(f"2. IDs en matches_liga_mx.csv: {len(mx_ids)} partidos generales")
        except Exception as e:
            print(f"   ⚠️ No se pudo leer matches_liga_mx.csv: {e}")

    # 3. Cargar IDs reales presentes en events_master.csv
    events_file = processed_dir / "events_master.csv"
    events_ids = set()
    if events_file.exists():
        df_ev_ids = pd.read_csv(events_file, usecols=['match_id'], low_memory=False)
        events_ids = set(df_ev_ids['match_id'].dropna().unique())
        print(f"3. IDs en events_master.csv: {len(events_ids)} partidos")

    # 4. Cargar IDs reales en frames_360_master.csv
    frames_file = processed_dir / "frames_360_master.csv"
    frames_ids = set()
    if frames_file.exists():
        df_360_ids = pd.read_csv(frames_file, usecols=['match_id'], low_memory=False)
        frames_ids = set(df_360_ids['match_id'].dropna().unique())
        print(f"4. IDs en frames_360_master.csv: {len(frames_ids)} partidos")

    # 5. Mapeo de la diferencia de los 5 partidos del inventario previo
    print("\n------------------------------------------------------------------")
    print("🔎 AUDITORÍA DE CANONICAL STAGES (NORMALIZACIÓN DE FASES):")
    print("------------------------------------------------------------------")

    # Definir función de asignación de fase canónica libre de solapamientos
    def get_canonical_stage(stage_raw):
        stage_str = str(stage_raw).lower()
        if 'quarter' in stage_str or 'semi' in stage_str or 'final' in stage_str or 'play-off' in stage_str:
            if 'regular' in stage_str or stage_str in ['apertura', 'clausura']:
                return 'Fase Regular'
            elif 'play-off' in stage_str or 'play-in' in stage_str:
                return 'Play-In'
            else:
                return 'Liguilla'
        elif stage_str in ['apertura', 'clausura']:
            return 'Fase Regular'
        else:
            return 'Por Clasificar'

    df_jardine['stage_canonical'] = df_jardine['competition_stage'].apply(get_canonical_stage)
    
    # Imprimir tabla de reconciliación por Temporada y Fase Canónica
    summary = df_jardine.groupby(['season', 'stage_canonical', 'competition_stage']).agg(
        partidos=('match_id', 'count')
    ).reset_index()

    print(summary.to_string(index=False))

    # Guardar reporte de auditoría por partido único con metadatos completos
    audit_file = processed_dir / "audit_match_ids_reconciliation.csv"
    df_jardine.to_csv(audit_file, index=False, encoding="utf-8")
    print(f"\n✅ Reporte de reconciliación por match_id guardado en: {audit_file}")

if __name__ == "__main__":
    reconcile_match_ids()