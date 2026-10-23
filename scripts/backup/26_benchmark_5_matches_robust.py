"""
Paso 26: Auditoría Robusta de Benchmark sobre Muestra Real de 5 Partidos
ISAC 2026 - El Vuelo del Bicampeón (Fase 2)
"""

from pathlib import Path
import pandas as pd
import numpy as np
import json

DATA_DIR = Path(r"C:\Users\omarc\AI_Projects\Competitions\club-america-isac-2026\data")
PROCESSED_DIR = DATA_DIR / "processed"

# 5 Partidos seleccionados para el benchmark
BENCHMARK_MATCH_IDS = ["3889637", "3890250", "3900001", "3901100", "3901234"]

def run_benchmark_robust():
    print("==================================================================")
    print("🔬 AUDITORÍA ROBUSTA DE BENCHMARK (CARGA REAL 5 PARTIDOS CONTROL)")
    print("==================================================================\n")

    events_file = PROCESSED_DIR / "events_master.csv"
    if not events_file.exists():
        print(f"❌ Error: {events_file} no existe.")
        return

    # 1. Cargar archivo maestro de eventos
    df_ev = pd.read_csv(events_file, low_memory=False)
    
    # Normalización estricta de match_id como string sin ceros/espacios ni prefijos
    df_ev['match_id_str'] = df_ev['match_id'].astype(str).str.replace('match_', '').str.strip()

    # Filtrar la muestra de los 5 partidos
    df_b = df_ev[df_ev['match_id_str'].isin(BENCHMARK_MATCH_IDS)].copy()
    
    print(f"📖 Eventos totales cargados en dataset maestro: {len(df_ev):,}")
    print(f"📖 Eventos recuperados para los 5 partidos de control: {len(df_b):,} filas.")

    # Conteo por partido para verificar que NINGUNO esté en cero
    match_counts = df_b.groupby('match_id_str')['event_id'].count().to_dict()
    print("\n   ✔️ Conteo de eventos recuperados por match_id:")
    for m_id in BENCHMARK_MATCH_IDS:
        cnt = match_counts.get(m_id, 0)
        print(f"      • Match ID {m_id}: {cnt:,} eventos")

    if any(cnt == 0 for cnt in [match_counts.get(m_id, 0) for m_id in BENCHMARK_MATCH_IDS]):
        print("\n❌ ALERTA CRÍTICA: Uno o más partidos siguen reportando 0 eventos. Verificando valores en fuente...")
        print("Valores únicos de match_id_str en df_ev (muestra primeros 10):", df_ev['match_id_str'].unique()[:10])

    # ------------------------------------------------------------------
    # 1. VERIFICACIÓN DE ORIENTACIÓN ESPACIAL POR TIROS (SISTEMA STATSBOMB)
    # ------------------------------------------------------------------
    print("\n1. VERIFICACIÓN DE DIRECCIÓN DE ATAQUE POR DISPAROS (X Promedio hacia X=120):")
    print("-" * 65)

    shots_df = df_b[df_b['type'] == 'Shot'].copy()
    
    for m_id in BENCHMARK_MATCH_IDS:
        m_shots = shots_df[shots_df['match_id_str'] == m_id]
        print(f"\n• Partido ID {m_id} (Total disparos: {len(m_shots)}):")
        
        shots_summary = m_shots.groupby(['period', 'is_america_action']).agg(
            total_tiros=('event_id', 'count'),
            promedio_x=('location_x', 'mean'),
            promedio_y=('location_y', 'mean')
        ).reset_index()

        for _, row in shots_summary.iterrows():
            team_str = "América" if row['is_america_action'] else "Rival"
            print(f"   - Periodo {int(row['period'])} | {team_str:<8} | Tiros: {int(row['total_tiros']):<2} | Coordenada X Promedio: {row['promedio_x']:.2f} (Objetivo Portería: 120, 40)")

    # ------------------------------------------------------------------
    # 2. FIELD TILT Y PPDA POR PARTIDO (5 PARTIDOS CONTROL)
    # ------------------------------------------------------------------
    print("\n2. FIELD TILT Y PPDA CALCULADOS POR PARTIDO:")
    print("-" * 65)

    benchmark_metrics = []
    for m_id in BENCHMARK_MATCH_IDS:
        grp = df_b[(df_b['match_id_str'] == m_id) & (df_b['period'] <= 4)]
        
        # Pases completados
        pases = grp[(grp['type'] == 'Pass') & (grp['pass_outcome'].isna())]
        
        # Field Tilt (Pases en X >= 80 en coordenadas de StatsBomb)
        ame_att = len(pases[(pases['is_america_action']) & (pases['location_x'] >= 80)])
        riv_att = len(pases[(~pases['is_america_action']) & (pases['location_x'] >= 80)])
        tot_att = ame_att + riv_att
        ft = (ame_att / tot_att * 100) if tot_att > 0 else np.nan

        # PPDA
        pases_riv_def = len(pases[(~pases['is_america_action']) & (pases['location_x'] <= 60)])
        def_actions_ame = len(grp[(grp['is_america_action']) & 
                                  (grp['type'].isin(['Tackle', 'Interception', 'Foul Committed', 'Duel', 'Block'])) & 
                                  (grp['location_x'] >= 60)])
        ppda = (pases_riv_def / def_actions_ame) if def_actions_ame > 0 else np.nan

        benchmark_metrics.append({
            'match_id': m_id,
            'pases_ultimo_tercio_ame': ame_att,
            'pases_ultimo_tercio_riv': riv_att,
            'field_tilt (%)': round(ft, 2) if pd.notna(ft) else np.nan,
            'pases_rival_zona_def': pases_riv_def,
            'acciones_def_ame': def_actions_ame,
            'ppda': round(ppda, 2) if pd.notna(ppda) else np.nan
        })

    df_res = pd.DataFrame(benchmark_metrics)
    print(df_res.to_string(index=False))

    # ------------------------------------------------------------------
    # 3. PASES PROGRESIVOS Y DESGLOSE DE PASS_TYPE (REGLA CONGELADA)
    # ------------------------------------------------------------------
    print("\n3. PASES PROGRESIVOS Y DESGLOSE POR PASS_TYPE (MUESTRA 5 PARTIDOS):")
    print("-" * 65)

    completed_passes = df_b[(df_b['type'] == 'Pass') & (df_b['pass_outcome'].isna()) & (df_b['end_location_x'].notna())].copy()
    
    # Verificación de pass_type
    if 'pass_type' in completed_passes.columns:
        pass_type_series = completed_passes['pass_type'].fillna('Juego Abierto (Null)')
    else:
        # Si no existe pass_type en events_master, se deriva de type/play_pattern
        pass_type_series = np.where(completed_passes['play_pattern'].isin(['From Corner', 'From Free Kick', 'From Throw In', 'From Kick Off', 'From Goal Kick']), 
                                    completed_passes['play_pattern'], 'Juego Abierto (Null)')
        completed_passes['pass_type_derived'] = pass_type_series

    print("   📊 Desglose de Pases Completados por Categoría:")
    print(pd.Series(pass_type_series).value_counts().to_string())

    is_open_play = pd.Series(pass_type_series).isin(['Juego Abierto (Null)', 'Recovery', 'Interception'])
    open_play_passes = completed_passes[is_open_play.values].copy()

    # Algoritmo de pase progresivo
    dist_start = np.sqrt((120 - open_play_passes['location_x'])**2 + (40 - open_play_passes['location_y'])**2)
    dist_end = np.sqrt((120 - open_play_passes['end_location_x'])**2 + (40 - open_play_passes['end_location_y'])**2)

    cond_prog = (
        ((open_play_passes['location_x'] < 40) & (dist_end <= dist_start * 0.70)) |
        ((open_play_passes['location_x'] >= 40) & (open_play_passes['location_x'] < 80) & (dist_end <= dist_start * 0.85)) |
        ((open_play_passes['location_x'] >= 80) & ((dist_end <= dist_start * 0.90) | (open_play_passes['end_location_x'] >= 102)))
    )

    prog_cnt = cond_prog.sum()

    print(f"\n   ✔️ Total Pases Completados Evaluados: {len(completed_passes):,}")
    print(f"   ✔️ Pases en Juego Abierto: {len(open_play_passes):,}")
    print(f"   ✔️ Pases Progresivos Identificados: {prog_cnt:,} ({prog_cnt / max(1, len(open_play_passes)) * 100:.2f}%)")

    # ------------------------------------------------------------------
    # 4. TRANSICIONES DEFENSIVAS CON PRIMER EVENTO TERMINAL
    # ------------------------------------------------------------------
    print("\n4. CLASIFICACIÓN DE TRANSICIONES DEFENSIVAS ($R_{10}$):")
    print("-" * 65)

    turnovers = df_b[(df_b['is_america_action']) & (df_b['period'] <= 4) & (
        (df_b['pass_outcome'].isin(['Incomplete', 'Out', 'Pass Offside'])) |
        (df_b['type'].isin(['Dispossessed', 'Error']))
    )].copy()

    c_rec, c_foul, c_shot, c_cont = 0, 0, 0, 0

    for idx, to in turnovers.iterrows():
        m_id = to['match_id_str']
        to_time = to['minute'] * 60 + to['second']
        
        win_evts = df_b[(df_b['match_id_str'] == m_id) & (df_b['period'] <= 4)].copy()
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

    tot_to = len(turnovers)
    print(f"   ✔️ Pérdidas totales de balón de América: {tot_to:,}")
    print(f"      1. Recuperación Efectiva (<= 10s): {c_rec} ({c_rec/max(1, tot_to)*100:.2f}%)")
    print(f"      2. Interrupción por Falta Cometida (<= 10s): {c_foul} ({c_foul/max(1, tot_to)*100:.2f}%)")
    print(f"      3. Remate Concedido al Rival (<= 10s): {c_shot} ({c_shot/max(1, tot_to)*100:.2f}%)")
    print(f"      4. Transición Continuada / Sin Acción Inmediata: {c_cont} ({c_cont/max(1, tot_to)*100:.2f}%)")

    # Guardar reporte JSON definitivo
    out_file = PROCESSED_DIR / "audit_benchmark_5_matches_robust.json"
    audit_data = {
        "fase": "2.3 - Auditoría Muestra Control 5 Partidos (Robusta)",
        "partidos_evaluados": BENCHMARK_MATCH_IDS,
        "eventos_totales_sample": len(df_b),
        "field_tilt_media_sample": round(df_res['field_tilt (%)'].mean(), 2),
        "ppda_media_sample": round(df_res['ppda'].mean(), 2),
        "pases_juego_abierto": len(open_play_passes),
        "pases_progresivos": int(prog_cnt),
        "turnovers_totales": tot_to
    }

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(audit_data, f, indent=4, ensure_ascii=False)

    print("\n==================================================================")
    print(f"✅ BENCHMARK ROBUSTO COMPLETADO EXITOSAMENTE. REPORTE EN: {out_file.name}")
    print("==================================================================")

if __name__ == "__main__":
    run_benchmark_robust()