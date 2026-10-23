"""
Paso 02: Reconciliación del Universo de Partidos (G1 y G2)
Fase 1.1 - ISAC 2026
"""

import json
from pathlib import Path
import pandas as pd

DATA_DIR = Path(r"C:\Users\omarc\AI_Projects\Competitions\club-america-isac-2026\data")

def reconcile_matches():
    print("==================================================================")
    print("📋 EJECUTANDO RECONCILIACIÓN REAL DEL UNIVERSO DE PARTIDOS")
    print("==================================================================\n")

    raw_dir = DATA_DIR / "raw"
    processed_dir = DATA_DIR / "processed"

    # 1. Leer el índice oficial de partidos de Jardine
    index_file = raw_dir / "jardine_matches_index.json"
    if not index_file.exists():
        print(f"❌ No se encontró {index_file}")
        return

    with open(index_file, "r", encoding="utf-8") as f:
        matches_data = json.load(f)

    df_matches = pd.DataFrame(matches_data)
    print(f"✔️ Metadatos de Jardine en raw: {len(df_matches)} registros leídos.")

    # 2. Inspeccionar los match_ids reales presentes en events_master.csv
    events_master_file = processed_dir / "events_master.csv"
    matches_in_events = set()
    if events_master_file.exists():
        print("📖 Leyendo match_ids únicos en events_master.csv...")
        # Leemos solo la columna match_id para velocidad
        df_ev_ids = pd.read_csv(events_master_file, usecols=['match_id'], low_memory=False)
        matches_in_events = set(df_ev_ids['match_id'].dropna().unique())
        print(f"✔️ Partidos únicos encontrados en events_master.csv: {len(matches_in_events)}")

    # 3. Inspeccionar los match_ids reales en frames_360_master.csv
    frames_master_file = processed_dir / "frames_360_master.csv"
    matches_in_360 = set()
    if frames_master_file.exists():
        print("📖 Leyendo match_ids únicos en frames_360_master.csv...")
        df_360_ids = pd.read_csv(frames_master_file, usecols=['match_id'], low_memory=False)
        matches_in_360 = set(df_360_ids['match_id'].dropna().unique())
        print(f"✔️ Partidos únicos encontrados en frames_360_master.csv: {len(matches_in_360)}")

    # 4. Cruce y Auditoría
    df_matches['has_events'] = df_matches['match_id'].isin(matches_in_events)
    df_matches['has_360'] = df_matches['match_id'].isin(matches_in_360)

    # Agrupación por Torneo/Temporada y Fase
    print("\n📊 DESGLOSE OBSERVADO POR COMPETICIÓN Y FASE:")
    print("-" * 65)
    
    # Identificar columnas de torneo y fase en los metadatos
    season_col = 'season_name' if 'season_name' in df_matches.columns else 'season'
    stage_col = 'stage_name' if 'stage_name' in df_matches.columns else 'stage'

    cols_to_group = [c for c in [season_col, stage_col] if c in df_matches.columns]
    
    if cols_to_group:
        summary = df_matches.groupby(cols_to_group).agg(
            total_partidos=('match_id', 'count'),
            con_eventos=('has_events', 'sum'),
            con_360=('has_360', 'sum')
        ).reset_index()
        print(summary.to_string(index=False))
    else:
        print("Columnas de temporada/fase no encontradas. Columnas disponibles:")
        print(list(df_matches.columns))

    # Guardar manifiesto real en processed
    manifest_path = processed_dir / "jardine_matches_manifest_audited.csv"
    df_matches.to_csv(manifest_path, index=False, encoding="utf-8")
    print(f"\n✅ Manifiesto de partidos auditado guardado en: {manifest_path}")

if __name__ == "__main__":
    reconcile_matches()