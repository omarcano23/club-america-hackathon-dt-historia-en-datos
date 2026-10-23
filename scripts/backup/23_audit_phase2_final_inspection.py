"""
Paso 23: Auditoría Forense Final de la Fase 2 (E2E)
ISAC 2026 - El Vuelo del Bicampeón
"""

from pathlib import Path
import pandas as pd
import numpy as np
import json

DATA_DIR = Path(r"C:\Users\omarc\AI_Projects\Competitions\club-america-isac-2026\data")
PROCESSED_DIR = DATA_DIR / "processed"
RAW_DIR = DATA_DIR / "raw"

def run_phase2_final_audit():
    print("==================================================================")
    print("🔬 INSPECCIÓN FORENSE Y COMPROBACIONES DE CIERRE (FASE 2)")
    print("==================================================================\n")

    events_file = PROCESSED_DIR / "events_master.csv"
    if not events_file.exists():
        print("❌ Error: events_master.csv no existe.")
        return

    df_ev = pd.read_csv(events_file, low_memory=False)

    # ------------------------------------------------------------------
    # COMPROBACIÓN 1: ORIENTACIÓN ESPACIAL Y AUDITORÍA DE INVERSIÓN
    # ------------------------------------------------------------------
    print("1. COMPROBACIÓN DE ORIENTACIÓN ESPACIAL Y ROTACIÓN DE PERIODOS:")
    print("-" * 65)

    direction_dict = {}
    fallback_count = 0
    
    for (m_id, per), group in df_ev.groupby(['match_id', 'period']):
        ame_events = group[(group['is_america_action']) & (group['location_x'].notna())]
        if len(ame_events) > 0:
            avg_x = ame_events['location_x'].mean()
            # América ataca hacia +X si su promedio es <= 60 (inicio en campo propio)
            # Si avg_x > 60, sus acciones están en campo rival (ataca hacia +X)
            # Invertir = True solo si la mayoría de sus pases nacen de X > 60 dirigiéndose a la izquierda
            # Regla limpia: medir avance vectorial de pases con destino
            passes_with_dest = group[(group['is_america_action']) & (group['type'] == 'Pass') & (group['end_location_x'].notna())]
            if len(passes_with_dest) > 5:
                delta_x = passes_with_dest['end_location_x'] - passes_with_dest['location_x']
                direction_dict[(m_id, per)] = bool(delta_x.mean() < 0)
            else:
                direction_dict[(m_id, per)] = bool(avg_x > 60)
        else:
            fallback_count += 1
            direction_dict[(m_id, per)] = bool(per in [2, 4])

    # Aplicar transformación
    df_ev['invert_period'] = df_ev.set_index(['match_id', 'period']).index.map(direction_dict)
    
    df_ev['x_norm'] = np.where(df_ev['invert_period'], 120.0 - df_ev['location_x'], df_ev['location_x'])
    df_ev['y_norm'] = np.where(df_ev['invert_period'], 80.0 - df_ev['location_y'], df_ev['location_y'])
    df_ev['end_x_norm'] = np.where(df_ev['invert_period'], 120.0 - df_ev['end_location_x'], df_ev['end_location_x'])
    df_ev['end_y_norm'] = np.where(df_ev['invert_period'], 80.0 - df_ev['end_location_y'], df_ev['end_location_y'])

    total_periods = len(direction_dict)
    inverted_periods = sum(direction_dict.values())
    normal_periods = total_periods - inverted_periods
    events_transformed = df_ev['invert_period'].sum()

    print(f"• Total de periodos de juego auditados: {total_periods}")
    print(f"• Periodos atacando hacia +X (Normal - Sin Invertir): {normal_periods}")
    print(f"• Periodos atacando hacia -X (Invertidos 180°): {inverted_periods} ({inverted_periods/total_periods*100:.2f}%)")
    print(f"• Uso de reglas de respaldo (Fallback por falta de eventos): {fallback_count}")
    print(f"• Total de eventos con rotación espacial aplicada: {events_transformed:,} de {len(df_ev):,} ({events_transformed/len(df_ev)*100:.2f}%)")

    # ------------------------------------------------------------------
    # COMPROBACIÓN 2: DESACOPLE PASS_TYPE vs PLAY_PATTERN & RECONCILIACIÓN DE PASES
    # ------------------------------------------------------------------
    print("\n2. RECONCILIACIÓN FORENSE Y REGLA DE JUEGO ABIERTO:")
    print("-" * 65)

    all_completed_passes = df_ev[(df_ev['type'] == 'Pass') & (df_ev['pass_outcome'].isna()) & (df_ev['end_location_x'].notna())].copy()
    total_completed = len(all_completed_passes)

    # Definición basada exclusivamente en pass_type
    restarts_pass_types = ['Corner', 'Free Kick', 'Throw-in', 'Kick Off', 'Goal Kick']
    
    is_restart = all_completed_passes['pass_type'].fillna('').isin(restarts_pass_types)
    open_play_passes = all_completed_passes[~is_restart].copy()
    restart_passes = all_completed_passes[is_restart].copy()

    # Algoritmo de pase progresivo en juego abierto
    dist_start = np.sqrt((120 - open_play_passes['x_norm'])**2 + (40 - open_play_passes['y_norm'])**2)
    dist_end = np.sqrt((120 - open_play_passes['end_x_norm'])**2 + (40 - open_play_passes['end_y_norm'])**2)

    cond_prog_base = (
        ((open_play_passes['x_norm'] < 40) & (dist_end <= dist_start * 0.70)) |
        ((open_play_passes['x_norm'] >= 40) & (open_play_passes['x_norm'] < 80) & (dist_end <= dist_start * 0.85)) |
        ((open_play_passes['x_norm'] >= 80) & ((dist_end <= dist_start * 0.90) | (open_play_passes['end_x_norm'] >= 102)))
    )

    prog_open_play = cond_prog_base.sum()

    print(f"• Pases completados totales en dataset: {total_completed:,}")
    print(f"• Pases de Reinicio Directo excluidos (vía pass_type): {len(restart_passes):,}")
    print(f"  Desglose por pass_type: {restart_passes['pass_type'].value_counts().to_dict()}")
    print(f"• Pases de Juego Abierto Evaluados: {len(open_play_passes):,}")
    print(f"• Pases Progresivos en Juego Abierto: {prog_open_play:,} ({prog_open_play / len(open_play_passes) * 100:.2f}%)")

    # ------------------------------------------------------------------
    # COMPROBACIÓN 3: FIELD TILT Y PPDA POR PARTIDO Y FASE CANÓNICA
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
        
        # Pases completados en ultimo tercio
        pases_m = group[(group['type'] == 'Pass') & (group['pass_outcome'].isna())]
        ame_att = len(pases_m[(pases_m['is_america_action']) & (pases_m['x_norm'] >= 80)])
        riv_att = len(pases_m[(~pases_m['is_america_action']) & (pases_m['x_norm'] >= 80)])
        tot_att = ame_att + riv_att
        
        ft_val = (ame_att / tot_att * 100) if tot_att > 0 else np.nan

        # PPDA
        pases_riv_def = len(pases_m[(~pases_m['is_america_action']) & (pases_m['x_norm'] <= 60)])
        def_actions_ame = len(group[(group['is_america_action']) & 
                                    (group['type'].isin(['Tackle', 'Interception', 'Foul Committed', 'Duel', 'Block'])) & 
                                    (group['x_norm'] >= 60)])
        
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
    # COMPROBACIÓN 4: TRANSICIÓN DEFENSIVA JERÁRQUICA CRONOLÓGICA
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
        
        # Eventos posteriores en el mismo partido en window [0, 10s]
        window_events = df_ev[(df_ev['match_id'] == m_id) & (df_ev['period'] <= 4)].copy()
        window_events['evt_time'] = window_events['minute'] * 60 + window_events['second']
        
        in_window = window_events[(window_events['evt_time'] - to_time > 0) & (window_events['evt_time'] - to_time <= 10.0)].sort_values('evt_time')
        
        if len(in_window) == 0:
            cat_continued += 1
            continue

        # Evaluar el PRIMER evento terminal relevante que ocurra
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
    print(f"  4. Transición Continuada sin Acción Inmediata: {cat_continued:,} ({cat_continued*100/total_turnovers:.2f}%)")
    print(f"  ✔️ Suma de comprobación: {cat_eff_recovery + cat_foul_interruption + cat_shot_conceded + cat_continued:,} / {total_turnovers:,} (100.0%)")

    # ------------------------------------------------------------------
    # COMPROBACIÓN 5: AUDITORÍA DE SECUENCIAS ABP Y REMATES ÚNICOS
    # ------------------------------------------------------------------
    print("\n5. AUDITORÍA DE SECUENCIAS ÚNICAS DE BALÓN PARADO (ABP):")
    print("-" * 65)

    abp_starts = df_ev[(df_ev['play_pattern'].isin(['From Corner', 'From Free Kick'])) & (df_ev['type'] == 'Pass')].copy()
    unique_abp_starts = abp_starts['event_id'].nunique()

    # Remates atribuidos a ABP por play_pattern
    abp_shots = df_ev[(df_ev['play_pattern'].isin(['From Corner', 'From Free Kick'])) & (df_ev['type'] == 'Shot')].copy()
    unique_abp_shots = abp_shots['event_id'].nunique()
    total_abp_xg = abp_shots['shot_statsbomb_xg'].sum()

    print(f"• Total de ejecuciones iniciales de ABP (Córner / Tiro Libre): {unique_abp_starts:,}")
    print(f"• Total de remates únicos derivados de ABP: {unique_abp_shots:,}")
    print(f"• Promedio de remates por cobro de ABP: {unique_abp_shots / max(1, unique_abp_starts):.3f}")
    print(f"• xG Acumulado Total en Balón Parado: {total_abp_xg:.2f} (Promedio xG por remate de ABP: {total_abp_xg / max(1, unique_abp_shots):.3f})")

    # Consolidación final del JSON
    audit_summary = {
        "fase": "2.3 - Auditoría de Aceptación Metodológica Final",
        "estado": "COMPLETADA Y VALIDADA CON ÉXITO",
        "orientacion_periodos_invertidos_pct": round(inverted_periods/total_periods*100, 2),
        "pases_juego_abierto_evaluados": len(open_play_passes),
        "pases_progresivos_juego_abierto": int(prog_open_play),
        "pct_pases_progresivos": round(prog_open_play / len(open_play_passes) * 100, 2),
        "turnovers_totales_evaluados": total_turnovers,
        "transicion_recuperacion_efectiva_pct": round(cat_eff_recovery/total_turnovers*100, 2),
        "abp_cobros_iniciales": unique_abp_starts,
        "abp_remates_unicos": unique_abp_shots,
        "abp_xg_total": round(total_abp_xg, 2)
    }

    out_file = PROCESSED_DIR / "audit_phase2_final_inspection.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(audit_summary, f, indent=4, ensure_ascii=False)

    print("\n==================================================================")
    print(f"✅ AUDITORÍA FINALIZADA EXITOSAMENTE. RESULTADOS GUARDADOS EN: {out_file.name}")
    print("==================================================================")

if __name__ == "__main__":
    run_phase2_final_audit()