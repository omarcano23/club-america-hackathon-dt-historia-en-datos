"""
Paso 24: Script Definitivo de Auditoría de la Fase 2 (Corrección KeyError y Geometría)
ISAC 2026 - El Vuelo del Bicampeón
"""

from pathlib import Path
import pandas as pd
import numpy as np
import json

DATA_DIR = Path(r"C:\Users\omarc\AI_Projects\Competitions\club-america-isac-2026\data")
PROCESSED_DIR = DATA_DIR / "processed"
RAW_DIR = DATA_DIR / "raw"

def run_phase2_fixed_audit():
    print("==================================================================")
    print("🔬 INSPECCIÓN FORENSE Y COMPROBACIONES DE CIERRE (FASE 2 - FIX)")
    print("==================================================================\n")

    events_file = PROCESSED_DIR / "events_master.csv"
    if not events_file.exists():
        print(f"❌ Error: {events_file} no existe.")
        return

    df_ev = pd.read_csv(events_file, low_memory=False)
    print(f"📖 Total de eventos cargados: {len(df_ev):,}")

    # ------------------------------------------------------------------
    # 1. ESQUEMA ESPACIAL CANÓNICO EN STATSBOMB
    # ------------------------------------------------------------------
    print("\n1. VERIFICACIÓN DE GEOMETRÍA NATIVA Y COORDENADAS:")
    print("-" * 65)

    # En StatsBomb, X va de 0 a 120 en la dirección de ataque del equipo del evento.
    # Para evaluar el campo desde la perspectiva del América:
    # - Acciones de América: Ataque hacia X=120 (Último Tercio: X >= 80, Campo Propio: X <= 40).
    # - Acciones del Rival: Cuando el rival ataca, su Último Tercio es X >= 80 en sus propios eventos.
    
    df_valid_loc = df_ev[df_ev['location_x'].notna()].copy()
    print(f"• Eventos con coordenadas válidas: {len(df_valid_loc):,} ({len(df_valid_loc)/len(df_ev)*100:.2f}%)")
    print(f"• Eventos de América con location_x >= 80 (Último Tercio de América): {len(df_valid_loc[(df_valid_loc['is_america_action']) & (df_valid_loc['location_x'] >= 80)]):,}")
    print(f"• Eventos de Rivales con location_x >= 80 (Último Tercio del Rival): {len(df_valid_loc[(~df_valid_loc['is_america_action']) & (df_valid_loc['location_x'] >= 80)]):,}")

    # ------------------------------------------------------------------
    # 2. RECONCILIACIÓN FORENSE DE PASES Y FILTRADO DE REINICIOS
    # ------------------------------------------------------------------
    print("\n2. RECONCILIACIÓN FORENSE Y REGLA DE JUEGO ABIERTO:")
    print("-" * 65)

    # Pases completados
    all_completed = df_ev[(df_ev['type'] == 'Pass') & (df_ev['pass_outcome'].isna()) & (df_ev['end_location_x'].notna())].copy()
    total_completed = len(all_completed)

    # Filtrar reinicios usando play_pattern (ej. 'From Corner', 'From Free Kick', 'From Throw In', 'From Kick Off', 'From Goal Kick')
    restart_patterns = ['From Corner', 'From Free Kick', 'From Throw In', 'From Kick Off', 'From Goal Kick']
    
    is_restart_pattern = all_completed['play_pattern'].isin(restart_patterns)
    open_play_passes = all_completed[~is_restart_pattern].copy()
    restart_passes = all_completed[is_restart_pattern].copy()

    # Algoritmo de pase progresivo en juego abierto
    dist_start = np.sqrt((120 - open_play_passes['location_x'])**2 + (40 - open_play_passes['location_y'])**2)
    dist_end = np.sqrt((120 - open_play_passes['end_location_x'])**2 + (40 - open_play_passes['end_location_y'])**2)

    cond_prog_base = (
        ((open_play_passes['location_x'] < 40) & (dist_end <= dist_start * 0.70)) |
        ((open_play_passes['location_x'] >= 40) & (open_play_passes['location_x'] < 80) & (dist_end <= dist_start * 0.85)) |
        ((open_play_passes['location_x'] >= 80) & ((dist_end <= dist_start * 0.90) | (open_play_passes['end_location_x'] >= 102)))
    )

    prog_open_play = cond_prog_base.sum()

    print(f"• Pases completados totales en dataset: {total_completed:,}")
    print(f"• Pases de Reinicio Excluidos (vía play_pattern): {len(restart_passes):,}")
    print(f"  Desglose de Reinicios: {restart_passes['play_pattern'].value_counts().to_dict()}")
    print(f"• Pases de Juego Abierto Evaluados: {len(open_play_passes):,}")
    print(f"• Pases Progresivos en Juego Abierto: {prog_open_play:,} ({prog_open_play / len(open_play_passes) * 100:.2f}%)")

    # ------------------------------------------------------------------
    # 3. FIELD TILT Y PPDA DESAGREGADOS POR PARTIDO Y FASE
    # ------------------------------------------------------------------
    print("\n3. FIELD TILT Y PPDA DESAGREGADOS POR PARTIDO Y FASE CANÓNICA:")
    print("-" * 65)

    index_json = RAW_DIR / "jardine_matches_index.json"
    with open(index_json, "r", encoding="utf-8") as f:
        meta_json = json.load(f)
    df_meta = pd.DataFrame(meta_json)

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
    meta_stage_map = df_meta.set_index('match_id')['stage_canonical'].to_dict()

    match_metrics = []
    for m_id, group in df_ev[df_ev['period'] <= 4].groupby('match_id'):
        stage = meta_stage_map.get(m_id, 'Desconocida')
        
        # Field Tilt: Pases completados por América en X >= 80 vs Pases completados por Rival en X >= 80
        pases_m = group[(group['type'] == 'Pass') & (group['pass_outcome'].isna())]
        ame_att = len(pases_m[(pases_m['is_america_action']) & (pases_m['location_x'] >= 80)])
        riv_att = len(pases_m[(~pases_m['is_america_action']) & (pases_m['location_x'] >= 80)])
        tot_att = ame_att + riv_att
        
        ft_val = (ame_att / tot_att * 100) if tot_att > 0 else np.nan

        # PPDA: Pases del rival en su propio campo (X <= 60) / Acciones defensivas de América en campo rival (X >= 60)
        pases_riv_def = len(pases_m[(~pases_m['is_america_action']) & (pases_m['location_x'] <= 60)])
        def_actions_ame = len(group[(group['is_america_action']) & 
                                    (group['type'].isin(['Tackle', 'Interception', 'Foul Committed', 'Duel', 'Block'])) & 
                                    (group['location_x'] >= 60)])
        
        ppda_val = (pases_riv_def / def_actions_ame) if def_actions_ame > 0 else np.nan

        match_metrics.append({
            'match_id': m_id,
            'stage_canonical': stage,
            'field_tilt': ft_val,
            'ppda': ppda_val
        })

    df_m_metrics = pd.DataFrame(match_metrics)

    summary_phase = df_m_metrics.groupby('stage_canonical').agg(
        partidos=('match_id', 'count'),
        partidos_ft_validos=('field_tilt', 'count'),
        ft_media=('field_tilt', 'mean'),
        ft_mediana=('field_tilt', 'median'),
        ppda_media=('ppda', 'mean'),
        ppda_mediana=('ppda', 'median')
    ).reset_index()
    print(summary_phase.to_string(index=False))

    # ------------------------------------------------------------------
    # 4. CLASIFICACIÓN JERÁRQUICA CRONOLÓGICA EN TRANSICIONES ($R_{10}$)
    # ------------------------------------------------------------------
    print("\n4. CLASIFICACIÓN JERÁRQUICA CRONOLÓGICA EN TRANSICIONES ($R_{10}$):")
    print("-" * 65)

    turnovers = df_ev[(df_ev['is_america_action']) & (df_ev['period'] <= 4) & (
        (df_ev['pass_outcome'].isin(['Incomplete', 'Out', 'Pass Offside'])) |
        (df_ev['type'].isin(['Dispossessed', 'Error']))
    )].copy()

    total_turnovers = len(turnovers)

    cat_eff_recovery = 0
    cat_foul_interruption = 0
    cat_shot_conceded = 0
    cat_continued = 0

    for idx, to in turnovers.iterrows():
        m_id = to['match_id']
        to_time = to['minute'] * 60 + to['second']
        
        window_events = df_ev[(df_ev['match_id'] == m_id) & (df_ev['period'] <= 4)].copy()
        window_events['evt_time'] = window_events['minute'] * 60 + window_events['second']
        
        in_window = window_events[(window_events['evt_time'] - to_time > 0) & (window_events['evt_time'] - to_time <= 10.0)].sort_values('evt_time')
        
        if len(in_window) == 0:
            cat_continued += 1
            continue

        found_cat = False
        for _, evt in in_window.iterrows():
            if evt['is_america_action'] and evt['type'] in ['Interception', 'Tackle', 'Ball Recovery']:
                cat_eff_recovery += 1
                found_cat = True
                break
            elif evt['is_america_action'] and evt['type'] == 'Foul Committed':
                cat_foul_interruption += 1
                found_cat = True
                break
            elif (not evt['is_america_action']) and evt['type'] == 'Shot':
                cat_shot_conceded += 1
                found_cat = True
                break
        
        if not found_cat:
            cat_continued += 1

    print(f"• Total de pérdidas elegibles evaluadas: {total_turnovers:,}")
    print(f"  1. Recuperación Efectiva Cronológica (<= 10s): {cat_eff_recovery:,} ({cat_eff_recovery/total_turnovers*100:.2f}%)")
    print(f"  2. Interrupción Forzada por Falta (<= 10s): {cat_foul_interruption:,} ({cat_foul_interruption*100/total_turnovers:.2f}%)")
    print(f"  3. Remate Concedido en Transición (<= 10s): {cat_shot_conceded:,} ({cat_shot_conceded*100/total_turnovers:.2f}%)")
    print(f"  4. Transición Continuada / Sin Acción Inmediata: {cat_continued:,} ({cat_continued*100/total_turnovers:.2f}%)")

    # ------------------------------------------------------------------
    # 5. AUDITORÍA DE SECUENCIAS ÚNICAS Y REMATES EN ABP
    # ------------------------------------------------------------------
    print("\n5. AUDITORÍA DE SECUENCIAS ÚNICAS Y REMATES DE BALÓN PARADO (ABP):")
    print("-" * 65)

    abp_starts = df_ev[(df_ev['play_pattern'].isin(['From Corner', 'From Free Kick'])) & (df_ev['type'] == 'Pass')].copy()
    unique_abp_starts = abp_starts['event_id'].nunique()

    abp_shots = df_ev[(df_ev['play_pattern'].isin(['From Corner', 'From Free Kick'])) & (df_ev['type'] == 'Shot')].copy()
    unique_abp_shots = abp_shots['event_id'].nunique()
    total_abp_xg = abp_shots['shot_statsbomb_xg'].sum()

    print(f"• Cobros iniciales de ABP (Córner / Tiro Libre): {unique_abp_starts:,}")
    print(f"• Remates únicos derivados de ABP: {unique_abp_shots:,}")
    print(f"• xG Acumulado Total en Balón Parado: {total_abp_xg:.2f}")

    # Guardar reporte JSON definitivo
    output = {
        "fase": "2.3 - Aceptación Metodológica Final (Corregido)",
        "pases_juego_abierto": len(open_play_passes),
        "pases_progresivos_juego_abierto": int(prog_open_play),
        "pct_progreso_juego_abierto": round(prog_open_play / len(open_play_passes) * 100, 2),
        "field_tilt_mediana_regular": round(df_m_metrics[df_m_metrics['stage_canonical']=='Fase Regular']['field_tilt'].median(), 2),
        "ppda_mediana_regular": round(df_m_metrics[df_m_metrics['stage_canonical']=='Fase Regular']['ppda'].median(), 2),
        "turnovers_evaluados": total_turnovers,
        "abp_remates_unicos": unique_abp_shots
    }

    out_file = PROCESSED_DIR / "audit_phase2_fixed_results.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=4, ensure_ascii=False)

    print("\n==================================================================")
    print(f"✅ AUDITORÍA FINALIZADA SIN ERRORES DE LLAVE. REPORTE EN: {out_file.name}")
    print("==================================================================")

if __name__ == "__main__":
    run_phase2_fixed_audit()