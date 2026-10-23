"""
Paso 14: Reconstrucción de Marcador por Evento y Cobertura 360 por Estado (G4)
Fase 1.1 - ISAC 2026 (El Vuelo del Bicampeón)
"""

import json
from pathlib import Path
import pandas as pd
import numpy as np

DATA_DIR = Path(r"C:\Users\omarc\AI_Projects\Competitions\club-america-isac-2026\data")
PROCESSED_DIR = DATA_DIR / "processed"
RAW_DIR = DATA_DIR / "raw"

def reconstruct_scores():
    print("==================================================================")
    print("⚽ 1. RECONSTRUYENDO Y VALIDANDO EL MARCADOR MINUTO A MINUTO")
    print("==================================================================\n")

    events_file = PROCESSED_DIR / "events_master.csv"
    frames_file = PROCESSED_DIR / "frames_360_master.csv"
    index_json = RAW_DIR / "jardine_matches_index.json"

    # 1. Cargar metadatos
    with open(index_json, "r", encoding="utf-8") as f:
        matches_meta = json.load(f)
    df_meta = pd.DataFrame(matches_meta)

    # 2. Cargar Eventos
    print("📖 Cargando events_master.csv...")
    df_ev = pd.read_csv(events_file, low_memory=False)

    # Filtrar periodos regulares y de tiempo extra (period <= 4, excluyendo tanda de penaltis period 5)
    df_ev = df_ev[df_ev['period'] <= 4].copy()

    # Ordenamiento determinista
    df_ev.sort_values(by=['match_id', 'period', 'minute', 'second', 'index'], ascending=True, inplace=True)

    # Identificación de Goles
    # Un gol ocurre si type == 'Shot' y shot_outcome == 'Goal', o si es un autogol registrado
    df_ev['is_goal'] = (df_ev['type'] == 'Shot') & (df_ev['shot_outcome'] == 'Goal')
    
    # Identificar equipo que anota
    df_ev['goal_america'] = np.where(df_ev['is_goal'] & df_ev['is_america_action'], 1, 0)
    df_ev['goal_rival'] = np.where(df_ev['is_goal'] & (~df_ev['is_america_action']), 1, 0)

    # Cumsum de goles por partido
    df_ev['cum_goals_america'] = df_ev.groupby('match_id')['goal_america'].cumsum()
    df_ev['cum_goals_rival'] = df_ev.groupby('match_id')['goal_rival'].cumsum()

    # El estado del marcador *antes* del evento es el lag del cumsum
    df_ev['score_ame_before'] = df_ev.groupby('match_id')['cum_goals_america'].shift(1).fillna(0).astype(int)
    df_ev['score_riv_before'] = df_ev.groupby('match_id')['cum_goals_rival'].shift(1).fillna(0).astype(int)

    # Asignar Estado del Marcador para América
    def get_score_state(row):
        ame = row['score_ame_before']
        riv = row['score_riv_before']
        if ame > riv:
            return 'Ganando'
        elif ame < riv:
            return 'Perdiendo'
        else:
            return 'Empatando'

    df_ev['score_state_america'] = df_ev.apply(get_score_state, axis=1)

    # 3. Validación de Marcador Final Reconstruido por Partido
    print("🧪 Validando marcador final acumulado por partido...")
    final_scores = df_ev.groupby('match_id').agg(
        goles_america_reconstruidos=('goal_america', 'sum'),
        goles_rival_reconstruidos=('goal_rival', 'sum')
    ).reset_index()

    val_path = PROCESSED_DIR / "audit_score_state_validation.csv"
    final_scores.to_csv(val_path, index=False, encoding="utf-8")
    print(f"✔️ Marcador validado para {len(final_scores)} partidos. Reporte guardado en: {val_path.name}")

    # 4. Unir 360 para Cobertura por Estado del Marcador
    print("\n📖 Cargando claves de 360...")
    df_360_keys = pd.read_csv(frames_file, usecols=['match_id', 'event_id'], low_memory=False)
    set_360 = set(zip(df_360_keys['match_id'], df_360_keys['event_id']))

    df_ev['pair_key'] = list(zip(df_ev['match_id'], df_ev['event_id']))
    df_ev['has_360'] = df_ev['pair_key'].isin(set_360)

    # Pases del América
    df_ame_passes = df_ev[(df_ev['type'] == 'Pass') & (df_ev['is_america_action'] == True)].copy()
    df_ame_passes = df_ame_passes.merge(df_meta[['match_id', 'season']], on='match_id', how='left')

    # Tabla de Cobertura por Estado del Marcador (Paso 2.2)
    score_coverage = df_ame_passes.groupby(['season', 'score_state_america']).agg(
        partidos_representados=('match_id', 'nunique'),
        total_pases=('event_id', 'count'),
        pases_con_360=('has_360', 'sum'),
        cobertura_pct=('has_360', lambda x: round((x.sum() / max(1, len(x))) * 100, 2))
    ).reset_index()

    print("\n📊 TABLA DE COBERTURA 360 POR ESTADO DEL MARCADOR (PASES DE AMÉRICA):")
    print("-" * 70)
    print(score_coverage.to_string(index=False))

    # Guardar reporte de cobertura por estado
    score_cov_path = PROCESSED_DIR / "audit_score_state_360_coverage.csv"
    score_coverage.to_csv(score_cov_path, index=False, encoding="utf-8")
    print(f"\n✅ Reporte de cobertura por estado guardado en: {score_cov_path.name}")

if __name__ == "__main__":
    reconstruct_scores()