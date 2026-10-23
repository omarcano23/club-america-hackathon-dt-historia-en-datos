"""
Paso 28 (Fix JSON): Benchmark Completo de 5 Partidos Reales Confirmados
ISAC 2026 - El Vuelo del Bicampeón (Fase 2)
"""

from pathlib import Path
import pandas as pd
import numpy as np
import json

DATA_DIR = Path(r"C:\Users\omarc\AI_Projects\Competitions\club-america-isac-2026\data")
PROCESSED_DIR = DATA_DIR / "processed"

def run_real_benchmark_fixed():
    print("==================================================================")
    print("🔬 AUDITORÍA BENCHMARK SOBRE 5 PARTIDOS REALES CONFIRMADOS (COMPLETO)")
    print("==================================================================\n")

    events_file = PROCESSED_DIR / "events_master.csv"
    if not events_file.exists():
        print(f"❌ Error: {events_file} no existe.")
        return

    # 1. Cargar eventos y limpiar IDs
    df_ev = pd.read_csv(events_file, low_memory=False)
    df_ev['match_id_clean'] = pd.to_numeric(df_ev['match_id'].astype(str).str.replace('match_', ''), errors='coerce').fillna(0).astype('int64')

    # 2. Obtener lista de IDs reales disponibles
    available_ids = df_ev['match_id_clean'].unique()
    
    # Seleccionamos 5 partidos reales garantizados (el 3889637 + 4 adicionales)
    sample_ids = [3889637]
    other_ids = [int(m) for m in available_ids if m != 3889637]
    
    if len(other_ids) >= 4:
        step = len(other_ids) // 4
        sample_ids.extend([other_ids[0], other_ids[step], other_ids[step*2], other_ids[step*3]])

    sample_ids = [int(x) for x in sample_ids]
    print(f"🎯 5 Partidos seleccionados para la prueba de control: {sample_ids}\n")

    # Filtrar eventos de los 5 partidos
    df_b = df_ev[df_ev['match_id_clean'].isin(sample_ids)].copy()

    # Verificar conteos por partido
    print("📋 CONTEO DE EVENTOS POR PARTIDO DE CONTROL:")
    print("-" * 65)
    counts = df_b.groupby('match_id_clean')['event_id'].count().to_dict()
    for m_id in sample_ids:
        print(f"   • Match ID {m_id}: {counts.get(m_id, 0):>6,} eventos | ✔️ RECUPERADO")

    # ------------------------------------------------------------------
    # 1. DIRECCIÓN DE ATAQUE Y DISPAROS POR PARTIDO Y PERIODO
    # ------------------------------------------------------------------
    print("\n1. INSPECCIÓN MANUAL DE COORDENADAS DE DISPAROS POR PERIODO:")
    print("-" * 65)

    shots_df = df_b[df_b['type'] == 'Shot'].copy()
    
    for m_id in sample_ids:
        m_shots = shots_df[shots_df['match_id_clean'] == m_id]
        print(f"\n• Partido ID {m_id} (Total disparos: {len(m_shots)}):")
        
        if len(m_shots) == 0:
            print("   ⚠️ Sin disparos registrados.")
            continue

        shots_summary = m_shots.groupby(['period', 'is_america_action']).agg(
            total_tiros=('event_id', 'count'),
            promedio_x_origen=('location_x', 'mean')
        ).reset_index()

        for _, row in shots_summary.iterrows():
            team_str = "América" if row['is_america_action'] else "Rival"
            print(f"   - Periodo {int(row['period'])} | {team_str:<8} | Tiros: {int(row['total_tiros']):<2} | X Origen Promedio: {row['promedio_x_origen']:.2f} (Ataque a X=120)")

    # ------------------------------------------------------------------
    # 2. FIELD TILT Y PPDA CALCULADOS INDEPENDIENTEMENTE (5 PARTIDOS)
    # ------------------------------------------------------------------
    print("\n2. FIELD TILT Y PPDA CALCULADOS POR PARTIDO:")
    print("-" * 65)

    benchmark_metrics = []
    for m_id in sample_ids:
        grp = df_b[(df_b['match_id_clean'] == m_id) & (df_b['period'] <= 4)]
        
        # Pases completados
        pases = grp[(grp['type'] == 'Pass') & (grp['pass_outcome'].isna())]
        
        # Field Tilt (Pases en X >= 80)
        ame_att = len(pases[(pases['is_america_action']) & (pases['location_x'] >= 80)])
        riv_att = len(pases[(~pases['is_america_action']) & (pases['location_x'] >= 80)])
        tot_att = ame_att + riv_att
        ft = (ame_att / tot_att * 100) if tot_att > 0 else np.nan

        # PPDA
        riv_def_passes = len(pases[(~pases['is_america_action']) & (pases['location_x'] <= 60)])
        ame_def_actions = len(grp[(grp['is_america_action']) & 
                                  (grp['type'].isin(['Tackle', 'Interception', 'Foul Committed', 'Duel', 'Block'])) & 
                                  (grp['location_x'] >= 60)])
        ppda = (riv_def_passes / ame_def_actions) if ame_def_actions > 0 else np.nan

        benchmark_metrics.append({
            'match_id': int(m_id),
            'pases_ultimo_tercio_ame': int(ame_att),
            'pases_ultimo_tercio_riv': int(riv_att),
            'field_tilt (%)': round(float(ft), 2) if pd.notna(ft) else np.nan,
            'pases_rival_zona_def': int(riv_def_passes),
            'acciones_def_ame': int(ame_def_actions),
            'ppda': round(float(ppda), 2) if pd.notna(ppda) else np.nan
        })

    df_res = pd.DataFrame(benchmark_metrics)
    print(df_res.to_string(index=False))

    # ------------------------------------------------------------------
    # 3. RECONCILIACIÓN ESTRICTA DE PASES EN JUEGO ABIERTO
    # ------------------------------------------------------------------
    print("\n3. RECONCILIACIÓN ESTRICTA DE PASES EN JUEGO ABIERTO:")
    print("-" * 65)

    completed_passes = df_b[(df_b['type'] == 'Pass') & (df_b['pass_outcome'].isna()) & (df_b['end_location_x'].notna())].copy()
    
    restart_patterns = ['From Corner', 'From Free Kick', 'From Throw In', 'From Kick Off', 'From Goal Kick']
    is_restart = completed_passes['play_pattern'].isin(restart_patterns)
    
    open_play_passes = completed_passes[~is_restart].copy()

    # Algoritmo de pase progresivo
    dist_start = np.sqrt((120 - open_play_passes['location_x'])**2 + (40 - open_play_passes['location_y'])**2)
    dist_end = np.sqrt((120 - open_play_passes['end_location_x'])**2 + (40 - open_play_passes['end_location_y'])**2)

    cond_prog = (
        ((open_play_passes['location_x'] < 40) & (dist_end <= dist_start * 0.70)) |
        ((open_play_passes['location_x'] >= 40) & (open_play_passes['location_x'] < 80) & (dist_end <= dist_start * 0.85)) |
        ((open_play_passes['location_x'] >= 80) & ((dist_end <= dist_start * 0.90) | (open_play_passes['end_location_x'] >= 102)))
    )

    prog_cnt = int(cond_prog.sum())

    print(f"• Pases completados totales en la muestra benchmark: {len(completed_passes):,}")
    print(f"• Pases en Juego Abierto: {len(open_play_passes):,}")
    print(f"• Pases Progresivos Identificados: {prog_cnt:,} ({prog_cnt / max(1, len(open_play_passes)) * 100:.2f}%)")

    # ------------------------------------------------------------------
    # 4. TRANSICIONES DEFENSIVAS CON CRONÓMETRO DE PRIMER EVENTO TERMINAL
    # ------------------------------------------------------------------
    print("\n4. CLASIFICACIÓN CON CRONÓMETRO DE PRIMER EVENTO TERMINAL ($R_{10}$):")
    print("-" * 65)

    turnovers = df_b[(df_b['is_america_action']) & (df_b['period'] <= 4) & (
        (df_b['pass_outcome'].isin(['Incomplete', 'Out', 'Pass Offside'])) |
        (df_b['type'].isin(['Dispossessed', 'Error']))
    )].copy()

    c_rec, c_foul, c_shot, c_cont = 0, 0, 0, 0

    for idx, to in turnovers.iterrows():
        m_id = to['match_id_clean']
        to_time = to['minute'] * 60 + to['second']
        
        win_evts = df_b[(df_b['match_id_clean'] == m_id) & (df_b['period'] <= 4)].copy()
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

    tot_to_b = len(turnovers)
    print(f"• Total de pérdidas evaluadas en los 5 partidos: {tot_to_b:,}")
    print(f"  1. Recuperación Efectiva (Primer Evento Terminal): {c_rec} ({c_rec/max(1, tot_to_b)*100:.2f}%)")
    print(f"  2. Interrupción por Falta Cometida: {c_foul} ({c_foul/max(1, tot_to_b)*100:.2f}%)")
    print(f"  3. Remate Concedido al Rival: {c_shot} ({c_shot/max(1, tot_to_b)*100:.2f}%)")
    print(f"  4. Transición Continuada sin Interrupción: {c_cont} ({c_cont/max(1, tot_to_b)*100:.2f}%)")

    # ------------------------------------------------------------------
    # 5. AUDITORÍA DE SECUENCIAS ÚNICAS Y REMATES DE BALÓN PARADO (ABP)
    # ------------------------------------------------------------------
    print("\n5. AUDITORÍA DE SECUENCIAS ÚNICAS Y REMATES EN BALÓN PARADO (ABP):")
    print("-" * 65)

    abp_starts_b = df_b[(df_b['play_pattern'].isin(['From Corner', 'From Free Kick'])) & (df_b['type'] == 'Pass')].copy()
    abp_shots_b = df_b[(df_b['play_pattern'].isin(['From Corner', 'From Free Kick'])) & (df_b['type'] == 'Shot')].copy()

    print(f"• Cobros iniciales de ABP identificados: {len(abp_starts_b):,}")
    print(f"• Remates únicos derivados de ABP: {len(abp_shots_b):,}")
    print(f"• xG Acumulado en ABP (Muestra 5 Partidos): {abp_shots_b['shot_statsbomb_xg'].sum():.2f}")

    # Guardar reporte JSON sin errores de serialización
    out_file = PROCESSED_DIR / "audit_benchmark_5_real_matches_results.json"
    audit_data = {
        "fase": "2.3 - Benchmark 5 Partidos Reales Confirmados",
        "partidos_recuperados": [int(x) for x in sample_ids],
        "eventos_totales_muestra": int(len(df_b)),
        "field_tilt_media": round(float(df_res['field_tilt (%)'].mean()), 2),
        "ppda_media": round(float(df_res['ppda'].mean()), 2),
        "pases_juego_abierto": int(len(open_play_passes)),
        "pases_progresivos": int(prog_cnt),
        "turnovers_evaluados": int(tot_to_b),
        "transicion_recuperacion_efectiva_pct": round(float(c_rec/max(1, tot_to_b)*100), 2)
    }

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(audit_data, f, indent=4, ensure_ascii=False)

    print("\n==================================================================")
    print(f"✅ BENCHMARK COMPLETADO Y GUARDADO EXITOSAMENTE EN: {out_file.name}")
    print("==================================================================")

if __name__ == "__main__":
    run_real_benchmark_fixed()