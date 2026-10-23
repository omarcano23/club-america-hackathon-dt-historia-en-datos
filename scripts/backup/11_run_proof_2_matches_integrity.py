"""
Prueba 2: Integridad por Partido (Maestro vs Raw JSONs)
Fase 1.1 - ISAC 2026 (El Vuelo del Bicampeón)
"""

import json
from pathlib import Path
import pandas as pd
import numpy as np

DATA_DIR = Path(r"C:\Users\omarc\AI_Projects\Competitions\club-america-isac-2026\data")
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"

def run_proof_2():
    print("==================================================================")
    print("🔬 EJECUTANDO PRUEBA 2: INTEGRIDAD PARTIDO A PARTIDO (G3, G4)")
    print("==================================================================\n")

    events_csv = PROCESSED_DIR / "events_master.csv"
    frames_csv = PROCESSED_DIR / "frames_360_master.csv"
    index_json = RAW_DIR / "jardine_matches_index.json"

    # 1. Cargar Metadatos de Partidos
    with open(index_json, "r", encoding="utf-8") as f:
        matches_meta = json.load(f)
    df_meta = pd.DataFrame(matches_meta)

    def classify_stage(stage_raw):
        stage_str = str(stage_raw).lower()
        if 'quarter' in stage_str or 'semi' in stage_str or 'final' in stage_str:
            if 'regular' in stage_str or stage_str in ['apertura', 'clausura']:
                return 'Fase Regular'
            elif 'play-off' in stage_str or 'play-in' in stage_str:
                return 'Play-In'
            else:
                return 'Liguilla'
        elif stage_str in ['apertura', 'clausura']:
            return 'Fase Regular'
        else:
            return 'Liguilla'

    df_meta['stage_canonical'] = df_meta['competition_stage'].apply(classify_stage)

    # 2. Cargar Eventos y 360 Maestro
    print("📖 Cargando eventos maestro...")
    cols_ev = ['match_id', 'event_id', 'type', 'location_x', 'location_y']
    df_ev = pd.read_csv(events_csv, usecols=cols_ev, low_memory=False)

    print("📖 Cargando 360 maestro...")
    df_360_keys = pd.read_csv(frames_csv, usecols=['match_id', 'event_id'], low_memory=False)
    unique_360_events = set(zip(df_360_keys['match_id'], df_360_keys['event_id']))

    df_ev['pair_key'] = list(zip(df_ev['match_id'], df_ev['event_id']))
    df_ev['has_360'] = df_ev['pair_key'].isin(unique_360_events)

    # 3. Leer conteos desde los JSON originales en raw/matches/
    print("📖 Contando eventos en archivos JSON originales de data/raw/matches/...")
    raw_counts = {}
    matches_dir = RAW_DIR / "matches"

    if matches_dir.exists():
        for match_folder in matches_dir.iterdir():
            if match_folder.is_dir():
                try:
                    m_id = int(match_folder.name)
                    json_path = match_folder / "events.json"
                    if json_path.exists():
                        with open(json_path, "r", encoding="utf-8") as f:
                            raw_events_data = json.load(f)
                            raw_counts[m_id] = len(raw_events_data)
                except ValueError:
                    continue

    # 4. Construir Resumen por Partido
    records = []
    for m_id, group in df_ev.groupby('match_id'):
        meta_row = df_meta[df_meta['match_id'] == m_id]
        season = meta_row['season'].values[0] if not meta_row.empty else 'Desconocida'
        stage = meta_row['stage_canonical'].values[0] if not meta_row.empty else 'Desconocida'

        events_total = len(group)
        passes_df = group[group['type'] == 'Pass']
        passes_total = len(passes_df)
        passes_with_360 = passes_df['has_360'].sum()
        pass_cov_pct = (passes_with_360 / max(1, passes_total)) * 100

        missing_loc = group['location_x'].isna().sum()
        out_of_bounds = len(group[(group['location_x'] < 0) | (group['location_x'] > 120) | (group['location_y'] < 0) | (group['location_y'] > 80)])

        raw_cnt = raw_counts.get(m_id, events_total)
        delta = events_total - raw_cnt

        records.append({
            'match_id': m_id,
            'season': season,
            'stage_canonical': stage,
            'events_total': events_total,
            'passes_total': passes_total,
            'passes_with_360': passes_with_360,
            'pass_360_coverage_pct': round(pass_cov_pct, 2),
            'events_missing_location': missing_loc,
            'events_out_of_range': out_of_bounds,
            'raw_events_count': raw_cnt,
            'event_count_delta': delta
        })

    df_summary = pd.DataFrame(records)
    out_path = PROCESSED_DIR / "audit_match_integrity_proof2.csv"
    df_summary.to_csv(out_path, index=False, encoding="utf-8")

    # 5. Imprimir los 5 entregables solicitados
    print("\n" + "="*65)
    print("RESULTADO — PRUEBA 2: INTEGRIDAD POR PARTIDO")
    print("="*65)

    delta_nonzero = len(df_summary[df_summary['event_count_delta'] != 0])
    print(f"1. Total de partidos con event_count_delta != 0: {delta_nonzero}")

    min_cov = df_summary['pass_360_coverage_pct'].min()
    max_cov = df_summary['pass_360_coverage_pct'].max()
    med_cov = df_summary['pass_360_coverage_pct'].median()
    print(f"2. Cobertura 360 en Pases (por partido): Mínimo = {min_cov}%, Máximo = {max_cov}%, Mediana = {med_cov}%")

    print("\n3. Los 5 partidos con menor cobertura de pases 360:")
    lowest_5 = df_summary.sort_values('pass_360_coverage_pct').head(5)
    print(lowest_5[['match_id', 'season', 'stage_canonical', 'passes_total', 'passes_with_360', 'pass_360_coverage_pct']].to_string(index=False))

    print("\n4. Desglose de eventos sin coordenadas por tipo de evento:")
    missing_loc_events = df_ev[df_ev['location_x'].isna()]['type'].value_counts()
    print(missing_loc_events.to_string())

    print(f"\n5. Diferencias encontradas entre JSON original y maestro: {delta_nonzero} partidos con diferencias.")
    print("="*65 + "\n")

if __name__ == "__main__":
    run_proof_2()