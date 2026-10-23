"""
Paso 25 (Corregido): Auditoría Forense Benchmark de 5 Partidos
ISAC 2026 - El Vuelo del Bicampeón
"""

from pathlib import Path
import pandas as pd
import numpy as np
import json

DATA_DIR = Path(r"C:\Users\omarc\AI_Projects\Competitions\club-america-isac-2026\data")
PROCESSED_DIR = DATA_DIR / "processed"

# 5 Partidos elegidos para el benchmark de control
BENCHMARK_MATCHES = [3889637, 3890250, 3900001, 3901100, 3901234]

def run_benchmark_fixed():
    print("==================================================================")
    print("🔬 AUDITORÍA MANUAL Y PRUEBA DE BENCHMARK (5 PARTIDOS CONTROL - FIX)")
    print("==================================================================\n")

    events_file = PROCESSED_DIR / "events_master.csv"
    if not events_file.exists():
        print("❌ Error: events_master.csv no existe.")
        return

    # 1. Cargar archivo maestro de eventos
    df_ev = pd.read_csv(events_file, low_memory=False)
    
    # Asegurar tipo de dato entero para match_id
    df_ev['match_id'] = pd.to_numeric(df_ev['match_id'], errors='coerce').fillna(0).astype(int)

    # Filtrar estrictamente la muestra de los 5 partidos
    df_b = df_ev[df_ev['match_id'].isin(BENCHMARK_MATCHES)].copy()
    print(f"📖 Eventos cargados para los 5 partidos de control: {len(df_b):,} filas.")

    if len(df_b) == 0:
        print("❌ Alerta: No se encontraron registros para los 5 match_id solicitados.")
        print(f"   IDs en df_ev: {df_ev['match_id'].unique()[:10]}")
        return

    # ------------------------------------------------------------------
    # PRUEBA 1: ORIENTACIÓN ESPACIAL POR DISPAROS (5 PARTIDOS)
    # ------------------------------------------------------------------
    print("\n1. VERIFICACIÓN DE ORIENTACIÓN ESPACIAL POR DISPAROS (5 PARTIDOS):")
    print("-" * 65)

    shots_df = df_b[df_b['type'] == 'Shot'].copy()
    
    for m_id in BENCHMARK_MATCHES:
        m_shots = shots_df[shots_df['match_id'] == m_id]
        print(f"• Partido ID {m_id} (Total disparos registrados: {len(m_shots)}):")
        if len(m_shots) == 0:
            print("   - Sin disparos registrados en este evento.")
            continue

        shots_check = m_shots.groupby(['period', 'is_america_action']).agg(
            total_tiros=('event_id', 'count'),
            promedio_x=('location_x', 'mean')
        ).reset_index()

        for _, row in shots_check.iterrows():
            team_str = "América" if row['is_america_action'] else "Rival"
            print(f"   - Periodo {int(row['period'])} | Equipo: {team_str:<8} | Tiros: {int(row['total_tiros']):<2} | X promedio: {row['promedio_x']:.2f}")

    # ------------------------------------------------------------------
    # PRUEBA 2: FIELD TILT Y PPDA POR PARTIDO
    # ------------------------------------------------------------------
    print("\n2. FIELD TILT Y PPDA POR PARTIDO (MUESTRA BENCHMARK):")
    print("-" * 65)

    benchmark_results = []
    for m_id in BENCHMARK_MATCHES:
        grp = df_b[(df_b['match_id'] == m_id) & (df_b['period'] <= 4)]
        
        # Pases completados en juego fluido
        pases = grp[(grp['type'] == 'Pass') & (grp['pass_outcome'].isna())]
        
        # Field Tilt (Pases en X >= 80 en coordenadas de StatsBomb)
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

        benchmark_results.append({
            'match_id': m_id,
            'pases_ultimo_tercio_ame': ame_att,
            'pases_ultimo_tercio_riv': riv_att,
            'field_tilt': round(ft, 2) if pd.notna(ft) else np.nan,
            'pases_rival_zona_def': riv_def_passes,
            'acciones_def_ame': ame_def_actions,
            'ppda': round(ppda, 2) if pd.notna(ppda) else np.nan
        })

    df_b_res = pd.DataFrame(benchmark_results)
    print(df_b_res.to_string(index=False))

    # ------------------------------------------------------------------
    # PRUEBA 3: RECONCILIACIÓN DE PASES PROGRESIVOS (MANEJO SEGURO DE COLUMNAS)
    # ------------------------------------------------------------------
    print("\n3. RECONCILIACIÓN DE PASES PROGRESIVOS Y DESGLOSE DE REINICIOS:")
    print("-" * 65)

    pases_b = df_b[(df_b['type'] == 'Pass') & (df_b['pass_outcome'].isna()) & (df_b['end_location_x'].notna())].copy()
    
    # Manejo seguro de columna de reinicios (vía play_pattern)
    restart_patterns = ['From Corner', 'From Free Kick', 'From Throw In', 'From Kick Off', 'From Goal Kick']
    has_restart_pattern = pases_b['play_pattern'].fillna('').isin(restart_patterns)
    
    open_play_b = pases_b[~has_restart_pattern].copy()
    restarts_b = pases_b[has_restart_pattern].copy()

    # Algoritmo de pase progresivo
    dist_start = np.sqrt((120 - open_play_b['location_x'])**2 + (40 - open_play_b['location_y'])**2)
    dist_end = np.sqrt((120 - open_play_b['end_location_x'])**2 + (40 - open_play_b['end_location_y'])**2)

    cond_prog = (
        ((open_play_b['location_x'] < 40) & (dist_end <= dist_start * 0.70)) |
        ((open_play_b['location_x'] >= 40) & (open_play_b['location_x'] < 80) & (dist_end <= dist_start * 0.85)) |
        ((open_play_b['location_x'] >= 80) & ((dist_end <= dist_start * 0.90) | (open_play_b['end_location_x'] >= 102)))
    )

    prog_b_cnt = cond_prog.sum()

    print(f"• Pases completados totales en la muestra benchmark: {len(pases_b):,}")
    print(f"• Reinicios excluidos (vía play_pattern): {len(restarts_b):,}")
    print(f"  Desglose: {restarts_b['play_pattern'].value_counts().to_dict()}")
    print(f"• Pases de Juego Abierto evaluados: {len(open_play_b):,}")
    print(f"• Pases Progresivos identificados: {prog_b_cnt:,} ({prog_b_cnt / max(1, len(open_play_b)) * 100:.2f}%)")

    # ------------------------------------------------------------------
    # PRUEBA 4: TRANSICIONES DEFENSIVAS CON CRONÓMETRO DE PRIMER EVENTO TERMINAL
    # ------------------------------------------------------------------
    print("\n4. CLASIFICACIÓN CON CRONÓMETRO DE PRIMER EVENTO TERMINAL ($R_{10}$):")
    print("-" * 65)

    to_b = df_b[(df_b['is_america_action']) & (df_b['period'] <= 4) & (
        (df_b['pass_outcome'].isin(['Incomplete', 'Out', 'Pass Offside'])) |
        (df_b['type'].isin(['Dispossessed', 'Error']))
    )].copy()

    c_rec, c_foul, c_shot, c_cont = 0, 0, 0, 0

    for idx, to in to_b.iterrows():
        m_id = to['match_id']
        to_time = to['minute'] * 60 + to['second']
        
        win_evts = df_b[(df_b['match_id'] == m_id) & (df_b['period'] <= 4)].copy()
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

    tot_to_b = len(to_b)
    print(f"• Total de pérdidas evaluadas en la muestra de control: {tot_to_b:,}")
    print(f"  1. Recuperación Efectiva (Primer Evento Terminal): {c_rec} ({c_rec/max(1, tot_to_b)*100:.2f}%)")
    print(f"  2. Interrupción por Falta Cometida: {c_foul} ({c_foul/max(1, tot_to_b)*100:.2f}%)")
    print(f"  3. Remate Concedido al Rival: {c_shot} ({c_shot/max(1, tot_to_b)*100:.2f}%)")
    print(f"  4. Transición Continuada sin Interrupción: {c_cont} ({c_cont/max(1, tot_to_b)*100:.2f}%)")

    # ------------------------------------------------------------------
    # PRUEBA 5: AUDITORÍA DE SECUENCIAS ÚNICAS Y REMATES DE BALÓN PARADO (ABP)
    # ------------------------------------------------------------------
    print("\n5. AUDITORÍA DE SECUENCIAS ÚNICAS Y REMATES EN BALÓN PARADO (ABP):")
    print("-" * 65)

    abp_starts_b = df_b[(df_b['play_pattern'].isin(['From Corner', 'From Free Kick'])) & (df_b['type'] == 'Pass')].copy()
    abp_shots_b = df_b[(df_b['play_pattern'].isin(['From Corner', 'From Free Kick'])) & (df_b['type'] == 'Shot')].copy()

    print(f"• Cobros iniciales de ABP identificados: {len(abp_starts_b):,}")
    print(f"• Remates únicos derivados de ABP: {len(abp_shots_b):,}")
    print(f"• xG Acumulado en ABP (Muestra Benchmark): {abp_shots_b['shot_statsbomb_xg'].sum():.2f}")

    # Guardar reporte oficial en JSON
    benchmark_summary = {
        "fase": "2.3 - Auditoría Muestra Benchmark (5 Partidos - Fix)",
        "partidos_evaluados": BENCHMARK_MATCHES,
        "pases_juego_abierto": len(open_play_b),
        "pases_progresivos": int(prog_b_cnt),
        "turnovers_evaluados": tot_to_b,
        "transicion_recuperacion_efectiva_pct": round(c_rec/max(1, tot_to_b)*100, 2)
    }

    out_file = PROCESSED_DIR / "audit_benchmark_5_matches_fixed.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(benchmark_summary, f, indent=4, ensure_ascii=False)

    print("\n==================================================================")
    print(f"✅ BENCHMARK FINALIZADO EXITOSAMENTE. REPORTE GUARDADO EN: {out_file.name}")
    print("==================================================================")

if __name__ == "__main__":
    run_benchmark_fixed()