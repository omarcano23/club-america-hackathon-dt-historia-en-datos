"""
Prueba 4: Auditoría de Representatividad y Sesgo de Cobertura 360 (G4)
Fase 1.1 - ISAC 2026 (El Vuelo del Bicampeón)
"""

import json
from pathlib import Path
import pandas as pd
import numpy as np

DATA_DIR = Path(r"C:\Users\omarc\AI_Projects\Competitions\club-america-isac-2026\data")
PROCESSED_DIR = DATA_DIR / "processed"
RAW_DIR = DATA_DIR / "raw"

GLOBAL_PASS_BENCHMARK = 87.25  # Cobertura ponderada global de pases auditada en la Prueba 1 y 2

def run_proof_4():
    print("==================================================================")
    print("🔬 EJECUTANDO PRUEBA 4: AUDITORÍA DE SESGO DE COBERTURA 360 (G4)")
    print("==================================================================\n")

    events_file = PROCESSED_DIR / "events_master.csv"
    frames_file = PROCESSED_DIR / "frames_360_master.csv"
    index_json = RAW_DIR / "jardine_matches_index.json"

    # 1. Cargar metadatos para fase canónica
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

    # 2. Cargar Pases y 360
    print("📖 Cargando eventos de pases...")
    cols_ev = ['match_id', 'event_id', 'type', 'period', 'team', 'is_america_action', 'pass_outcome', 'under_pressure']
    df_ev = pd.read_csv(events_file, usecols=cols_ev, low_memory=False)
    df_passes = df_ev[df_ev['type'] == 'Pass'].copy()

    # Unir metadatos
    df_passes = df_passes.merge(df_meta[['match_id', 'season', 'stage_canonical']], on='match_id', how='left')

    print("📖 Cargando claves 360...")
    df_360_keys = pd.read_csv(frames_file, usecols=['match_id', 'event_id'], low_memory=False)
    set_360_pairs = set(zip(df_360_keys['match_id'], df_360_keys['event_id']))

    df_passes['pair_key'] = list(zip(df_passes['match_id'], df_passes['event_id']))
    df_passes['has_360'] = df_passes['pair_key'].isin(set_360_pairs)

    # Categorización de Pases
    df_passes['equipo_label'] = np.where(df_passes['is_america_action'], 'América', 'Rival')
    df_passes['resultado_label'] = df_passes['pass_outcome'].fillna('Complete')

    # Función auxiliar de resumen por estrato
    def summarize_strata(df_subset, group_cols):
        summary = df_subset.groupby(group_cols).agg(
            total_partidos=('match_id', 'nunique'),
            total_pases=('event_id', 'count'),
            pases_con_360=('has_360', 'sum'),
            cobertura_pct=('has_360', lambda x: (x.sum() / max(1, len(x))) * 100)
        ).reset_index()
        summary['cobertura_pct'] = summary['cobertura_pct'].round(2)
        summary['diff_vs_global_pp'] = (summary['cobertura_pct'] - GLOBAL_PASS_BENCHMARK).round(2)
        return summary

    # A. Tabla por Temporada y Fase Canónica
    df_season_stage = summarize_strata(df_passes, ['season', 'stage_canonical'])

    # B. Tabla por Equipo y Periodo
    df_team_period = summarize_strata(df_passes, ['equipo_label', 'period'])

    # C. Tabla por Resultado del Pase
    df_outcome = summarize_strata(df_passes, ['resultado_label'])

    # D. Diagnóstico de los 5 partidos de menor cobertura
    df_by_match = summarize_strata(df_passes, ['match_id', 'season', 'stage_canonical'])
    lowest_5_matches = df_by_match.sort_values('cobertura_pct').head(5)

    print("\n" + "="*65)
    print("RESULTADO — PRUEBA 4: REPRESENTATIVIDAD DE COBERTURA 360")
    print("="*65)

    print("\n1. COBERTURA POR TEMPORADA Y FASE CANÓNICA:")
    print("-" * 65)
    print(df_season_stage.to_string(index=False))

    print("\n2. COBERTURA POR EQUIPO Y PERIODO DE JUEGO:")
    print("-" * 65)
    print(df_team_period.to_string(index=False))

    print("\n3. ESTRATOS EXTREMOS (MAYOR Y MENOR COBERTURA):")
    print("-" * 65)
    df_all_strata = pd.concat([
        df_season_stage.rename(columns={'stage_canonical': 'estrato'}).assign(tipo='Temporada-Fase'),
        df_team_period.rename(columns={'equipo_label': 'estrato'}).assign(tipo='Equipo-Periodo'),
        df_outcome.rename(columns={'resultado_label': 'estrato'}).assign(tipo='Resultado Pase')
    ], ignore_index=True)
    
    top_strata = df_all_strata.sort_values('cobertura_pct', ascending=False).head(3)
    bot_strata = df_all_strata.sort_values('cobertura_pct', ascending=True).head(3)
    
    print("Top 3 Estratos con mayor cobertura:")
    print(top_strata[['tipo', 'estrato', 'total_pases', 'cobertura_pct', 'diff_vs_global_pp']].to_string(index=False))
    print("\nTop 3 Estratos con menor cobertura:")
    print(bot_strata[['tipo', 'estrato', 'total_pases', 'cobertura_pct', 'diff_vs_global_pp']].to_string(index=False))

    print("\n4. DIAGNÓSTICO DE LOS 5 PARTIDOS CON MENOR COBERTURA:")
    print("-" * 65)
    print(lowest_5_matches[['match_id', 'season', 'stage_canonical', 'total_pases', 'pases_con_360', 'cobertura_pct', 'diff_vs_global_pp']].to_string(index=False))

    print("\n5. AUDITORÍA DE ESTADO DEL MARCADOR:")
    print("-" * 65)
    print("Estado: Variable PENDIENTE DE RECONSTRUCCIÓN.")
    print("Motivo: El campo directo de marcador por evento ('score', 'home_score', 'away_score') no está pre-calculado en events_master.csv. Se requiere derivar el marcador acumulado minuto a minuto procesando la secuencia de eventos de gol ('Shot' con outcome 'Goal') antes de auditar la cobertura por estado del marcador.")

    print("="*65 + "\n")

if __name__ == "__main__":
    run_proof_4()