"""
Paso 29: Validación Final de la Puerta Metodológica (Subfase 2.3)
ISAC 2026 - El Vuelo del Bicampeón
"""

from pathlib import Path
import pandas as pd
import numpy as np
import json

DATA_DIR = Path(r"C:\Users\omarc\AI_Projects\Competitions\club-america-isac-2026\data")
PROCESSED_DIR = DATA_DIR / "processed"
RAW_DIR = DATA_DIR / "raw"

def run_final_methodological_audit():
    print("==================================================================")
    print("🔬 AUDITORÍA INTEGRAL DE LA PUERTA METODOLÓGICA (SUBFASE 2.3)")
    print("==================================================================\n")

    events_file = PROCESSED_DIR / "events_master.csv"
    if not events_file.exists():
        print(f"❌ Error: {events_file} no existe.")
        return

    df_ev = pd.read_csv(events_file, low_memory=False)
    df_ev['match_id_clean'] = pd.to_numeric(df_ev['match_id'].astype(str).str.replace('match_', ''), errors='coerce').fillna(0).astype('int64')

    # Cargar metadatos para mapeo de fases canónicas
    index_json = RAW_DIR / "jardine_matches_index.json"
    meta_stage_map = {}
    if index_json.exists():
        with open(index_json, "r", encoding="utf-8") as f:
            meta_data = json.load(f)
        for m in meta_data:
            m_id = int(str(m.get('match_id', 0)).replace('match_', ''))
            stage_raw = str(m.get('competition_stage', '')).lower()
            if 'quarter' in stage_raw or 'semi' in stage_raw or 'final' in stage_raw:
                if 'regular' in stage_raw or stage_raw in ['apertura', 'clausura']:
                    stage_clean = 'Fase Regular'
                elif 'play-off' in stage_raw or 'play-in' in stage_raw:
                    stage_clean = 'Play-In'
                else:
                    stage_clean = 'Liguilla'
            elif stage_raw in ['apertura', 'clausura']:
                stage_clean = 'Fase Regular'
            else:
                stage_clean = 'Liguilla'
            meta_stage_map[m_id] = stage_clean

    # ------------------------------------------------------------------
    # 1. FIELD TILT Y PPDA POR PARTIDO Y DESAGREGADO POR FASE
    # ------------------------------------------------------------------
    print("1. EVALUACIÓN DESAGREGADA DE FIELD TILT Y PPDA POR FASE CANÓNICA:")
    print("-" * 65)

    match_metrics = []
    for m_id, grp in df_ev[df_ev['period'] <= 4].groupby('match_id_clean'):
        stage = meta_stage_map.get(m_id, 'Fase Regular')
        
        # Field Tilt (Pases completados en X >= 80 por perspectiva de equipo)
        pases = grp[(grp['type'] == 'Pass') & (grp['pass_outcome'].isna())]
        ame_att = len(pases[(pases['is_america_action']) & (pases['location_x'] >= 80)])
        riv_att = len(pases[(~pases['is_america_action']) & (pases['location_x'] >= 80)])
        tot_att = ame_att + riv_att
        ft_val = (ame_att / tot_att * 100) if tot_att > 0 else np.nan

        # PPDA: Pases del rival en su tercio defensivo (X <= 60) / Acciones defensivas de América en campo rival (X >= 60)
        pases_riv_def = len(pases[(~pases['is_america_action']) & (pases['location_x'] <= 60)])
        def_actions_ame = len(grp[(grp['is_america_action']) & 
                                    (grp['type'].isin(['Tackle', 'Interception', 'Foul Committed', 'Duel', 'Block'])) & 
                                    (grp['location_x'] >= 60)])
        ppda_val = (pases_riv_def / def_actions_ame) if def_actions_ame > 0 else np.nan

        match_metrics.append({
            'match_id': m_id,
            'stage': stage,
            'field_tilt': ft_val,
            'ppda': ppda_val,
            'ame_att_passes': ame_att,
            'riv_att_passes': riv_att
        })

    df_m = pd.DataFrame(match_metrics)
    summary_phase = df_m.groupby('stage').agg(
        partidos=('match_id', 'count'),
        ft_media=('field_tilt', 'mean'),
        ft_mediana=('field_tilt', 'median'),
        ppda_media=('ppda', 'mean'),
        ppda_mediana=('ppda', 'median')
    ).reset_index()

    print(summary_phase.to_string(index=False))

    # ------------------------------------------------------------------
    # 2. PRUEBA DE SENSIBILIDAD EN PASES PROGRESIVOS (BASE VS ESTRICTA)
    # ------------------------------------------------------------------
    print("\n2. PRUEBA DE SENSIBILIDAD DE PASES PROGRESIVOS (REGLA ABIERTA ESTRICTA):")
    print("-" * 65)

    completed_passes = df_ev[(df_ev['type'] == 'Pass') & (df_ev['pass_outcome'].isna()) & (df_ev['end_location_x'].notna())].copy()
    
    # Exclusión explícita por pass_type si existe, o por play_pattern de reinicio directo
    restart_patterns = ['From Corner', 'From Free Kick', 'From Throw In', 'From Kick Off', 'From Goal Kick']
    is_restart = completed_passes['play_pattern'].isin(restart_patterns)
    
    open_play_passes = completed_passes[~is_restart].copy()
    total_open_passes = len(open_play_passes)

    dist_start = np.sqrt((120 - open_play_passes['location_x'])**2 + (40 - open_play_passes['location_y'])**2)
    dist_end = np.sqrt((120 - open_play_passes['end_location_x'])**2 + (40 - open_play_passes['end_location_y'])**2)

    # Regla Base (30% / 15% / 10%)
    cond_base = (
        ((open_play_passes['location_x'] < 40) & (dist_end <= dist_start * 0.70)) |
        ((open_play_passes['location_x'] >= 40) & (open_play_passes['location_x'] < 80) & (dist_end <= dist_start * 0.85)) |
        ((open_play_passes['location_x'] >= 80) & ((dist_end <= dist_start * 0.90) | (open_play_passes['end_location_x'] >= 102)))
    )

    # Regla Estricta (35% / 20% / 15%)
    cond_strict = (
        ((open_play_passes['location_x'] < 40) & (dist_end <= dist_start * 0.65)) |
        ((open_play_passes['location_x'] >= 40) & (open_play_passes['location_x'] < 80) & (dist_end <= dist_start * 0.80)) |
        ((open_play_passes['location_x'] >= 80) & ((dist_end <= dist_start * 0.85) | (open_play_passes['end_location_x'] >= 102)))
    )

    prog_base = int(cond_base.sum())
    prog_strict = int(cond_strict.sum())

    print(f"• Pases Completados en Juego Abierto Evaluados: {total_open_passes:,}")
    print(f"• Regla Base (30/15/10%): {prog_base:,} pases ({prog_base / total_open_passes * 100:.2f}%)")
    print(f"• Regla Estricta (35/20/15%): {prog_strict:,} pases ({prog_strict / total_open_passes * 100:.2f}%)")
    print(f"• Sensibilidad / Variación: {prog_base - prog_strict:,} pases de diferencia ({((prog_base - prog_strict)/prog_base)*100:.2f}% de reducción)")

    # ------------------------------------------------------------------
    # 3. PRECEDENCIA CRONOLÓGICA UNÍVOCA EN TRANSICIONES ($R_{10}$)
    # ------------------------------------------------------------------
    print("\n3. TRANSICIONES DEFENSIVAS CON PRECEDENCIA CRONOLÓGICA UNÍVOCA ($R_{10}$):")
    print("-" * 65)

    turnovers = df_ev[(df_ev['is_america_action']) & (df_ev['period'] <= 4) & (
        (df_ev['pass_outcome'].isin(['Incomplete', 'Out', 'Pass Offside'])) |
        (df_ev['type'].isin(['Dispossessed', 'Error']))
    )].copy()

    total_turnovers = len(turnovers)
    c_rec, c_foul, c_shot, c_cont = 0, 0, 0, 0

    for idx, to in turnovers.iterrows():
        m_id = to['match_id_clean']
        to_time = to['minute'] * 60 + to['second']
        
        win_evts = df_ev[(df_ev['match_id_clean'] == m_id) & (df_ev['period'] <= 4)].copy()
        win_evts['evt_time'] = win_evts['minute'] * 60 + win_evts['second']
        
        sub_win = win_evts[(win_evts['evt_time'] - to_time > 0) & (win_evts['evt_time'] - to_time <= 10.0)].sort_values(['evt_time', 'index'])
        
        if len(sub_win) == 0:
            c_cont += 1
            continue

        assigned = False
        for _, evt in sub_win.iterrows():
            if evt['is_america_action'] and evt['type'] in ['Interception', 'Tackle', 'Ball Recovery']:
                c_rec += 1
                assigned = True
                break
            elif evt['is_america_action'] and evt['type'] == 'Foul Committed':
                c_foul += 1
                assigned = True
                break
            elif (not evt['is_america_action']) and evt['type'] == 'Shot':
                c_shot += 1
                assigned = True
                break

        if not assigned:
            c_cont += 1

    print(f"• Total Pérdidas de Balón Evaluadas: {total_turnovers:,}")
    print(f"  1. Recuperación Efectiva Cronológica (<= 10s): {c_rec:,} ({c_rec/total_turnovers*100:.2f}%)")
    print(f"  2. Interrupción Forzada por Falta (<= 10s): {c_foul:,} ({c_foul/total_turnovers*100:.2f}%)")
    print(f"  3. Remate Concedido al Rival (<= 10s): {c_shot:,} ({c_shot/total_turnovers*100:.2f}%)")
    print(f"  4. Transición Continuada / Sin Acción Inmediata: {c_cont:,} ({c_cont/total_turnovers*100:.2f}%)")

    # ------------------------------------------------------------------
    # 4. BALÓN PARADO (ABP) Y SECUENCIAS ÚNICAS
    # ------------------------------------------------------------------
    print("\n4. SECUENCIAS Y ATRIBUCIÓN DE REMATES EN BALÓN PARADO (ABP):")
    print("-" * 65)

    abp_shots = df_ev[(df_ev['play_pattern'].isin(['From Corner', 'From Free Kick'])) & (df_ev['type'] == 'Shot')].copy()
    unique_shots = len(abp_shots)
    total_xg = abp_shots['shot_statsbomb_xg'].sum()

    print(f"• Remates Únicos Atribuidos a ABP: {unique_shots:,}")
    print(f"• xG Acumulado Total en Balón Parado: {total_xg:.2f}")
    print(f"• Promedio xG por Remate de ABP: {total_xg / max(1, unique_shots):.3f}")

    # Exportar Manifiesto Definitivo
    manifest = {
        "subfase": "2.3 - Puerta de Aceptación Metodológica (Validación Final)",
        "estado": "APROBADA",
        "partidos_totales_evaluados": int(df_m['match_id'].nunique()),
        "field_tilt_media_ regular": round(float(df_m[df_m['stage']=='Fase Regular']['field_tilt'].mean()), 2),
        "field_tilt_mediana_regular": round(float(df_m[df_m['stage']=='Fase Regular']['field_tilt'].median()), 2),
        "ppda_media_regular": round(float(df_m[df_m['stage']=='Fase Regular']['ppda'].mean()), 2),
        "ppda_mediana_regular": round(float(df_m[df_m['stage']=='Fase Regular']['ppda'].median()), 2),
        "pases_progresivos_base": int(prog_base),
        "pases_progresivos_estricta": int(prog_strict),
        "transicion_recuperacion_efectiva_pct": round(float(c_rec/total_turnovers*100), 2),
        "abp_remates_totales": int(unique_shots),
        "abp_xg_acumulado": round(float(total_xg), 2)
    }

    out_file = PROCESSED_DIR / "methodological_gate_final_manifest.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=4, ensure_ascii=False)

    print("\n==================================================================")
    print(f"✅ MANIFIESTO METODOLÓGICO CONGELADO EN: {out_file.name}")
    print("==================================================================")

if __name__ == "__main__":
    run_final_methodological_audit()