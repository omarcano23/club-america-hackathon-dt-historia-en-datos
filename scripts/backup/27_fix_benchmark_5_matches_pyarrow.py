"""
Paso 27: Solución Definitiva de Carga PyArrow y Benchmark de 5 Partidos
ISAC 2026 - El Vuelo del Bicampeón (Fase 2)
"""

from pathlib import Path
import pandas as pd
import numpy as np
import json

DATA_DIR = Path(r"C:\Users\omarc\AI_Projects\Competitions\club-america-isac-2026\data")
PROCESSED_DIR = DATA_DIR / "processed"

# Lista numérica explícita de los 5 partidos
BENCHMARK_IDS = [3889637, 3890250, 3900001, 3901100, 3901234]

def run_pyarrow_benchmark_fix():
    print("==================================================================")
    print("🛠️ CORRECCIÓN DE SELECCIÓN Y AUDITORÍA BENCHMARK (5 PARTIDOS)")
    print("==================================================================\n")

    events_file = PROCESSED_DIR / "events_master.csv"
    if not events_file.exists():
        print(f"❌ Error: {events_file} no existe.")
        return

    # 1. Cargar datos forzando el tipo nativo
    df_ev = pd.read_csv(events_file, low_memory=False)
    
    # Casting explícito PyArrow -> NumPy int64 para eliminar la falla de comparación
    df_ev['match_id_clean'] = pd.to_numeric(df_ev['match_id'].astype(str).str.replace('match_', ''), errors='coerce').fillna(0).astype('int64')

    # Filtrar la muestra real
    df_b = df_ev[df_ev['match_id_clean'].isin(BENCHMARK_IDS)].copy()
    
    print(f"📖 Eventos totales en dataset maestro: {len(df_ev):,}")
    print(f"📖 Eventos RECUPERADOS REALES para los 5 partidos: {len(df_b):,} filas.\n")

    # 2. Comprobar que NINGÚN partido tenga 0 eventos
    print("📋 CONTEO REAL DE EVENTOS RECUPERADOS POR PARTIDO:")
    print("-" * 65)
    counts = df_b.groupby('match_id_clean')['event_id'].count().to_dict()
    
    all_loaded = True
    for m_id in BENCHMARK_IDS:
        cnt = counts.get(m_id, 0)
        status = "✔️ OK" if cnt > 0 else "❌ VACÍO"
        print(f"   • Match ID {m_id}: {cnt:>6,} eventos | {status}")
        if cnt == 0:
            all_loaded = False

    if not all_loaded:
        print("\n❌ ALERTA: Algunos partidos no están en events_master.csv con esos ID numéricos.")
        print("Muestra de IDs numéricos presentes en el maestro:", np.sort(df_ev['match_id_clean'].unique())[:15])
        return

    # ------------------------------------------------------------------
    # 1. VERIFICACIÓN DE DIRECCIÓN DE ATAQUE Y COORDENADAS POR DISPARO
    # ------------------------------------------------------------------
    print("\n1. INSPECCIÓN MANUAL DE COORDENADAS DE DISPAROS POR PARTIDO:")
    print("-" * 65)
    
    shots_df = df_b[df_b['type'] == 'Shot'].copy()
    
    for m_id in BENCHMARK_IDS:
        m_shots = shots_df[shots_df['match_id_clean'] == m_id]
        print(f"\n• Partido ID {m_id} (Total Disparos Registrados: {len(m_shots)}):")
        
        if len(m_shots) == 0:
            print("   ⚠️ Sin disparos registrados.")
            continue

        shots_summary = m_shots.groupby(['period', 'is_america_action']).agg(
            total_tiros=('event_id', 'count'),
            promedio_x_origen=('location_x', 'mean'),
            min_x_origen=('location_x', 'min'),
            max_x_origen=('location_x', 'max')
        ).reset_index()

        for _, row in shots_summary.iterrows():
            team_str = "América" if row['is_america_action'] else "Rival"
            print(f"   - Periodo {int(row['period'])} | {team_str:<8} | Tiros: {int(row['total_tiros']):<2} | X Origen Promedio: {row['promedio_x_origen']:.2f} (Rango: {row['min_x_origen']:.1f} - {row['max_x_origen']:.1f})")

    # ------------------------------------------------------------------
    # 2. FIELD TILT Y PPDA POR PARTIDO (RECONCILIADO EN LOS 5 PARTIDOS)
    # ------------------------------------------------------------------
    print("\n2. FIELD TILT Y PPDA CALCULADOS INDEPENDIENTEMENTE (5 PARTIDOS):")
    print("-" * 65)

    benchmark_metrics = []
    for m_id in BENCHMARK_IDS:
        grp = df_b[(df_b['match_id_clean'] == m_id) & (df_b['period'] <= 4)]
        
        # Pases completados
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

        benchmark_metrics.append({
            'match_id': m_id,
            'pases_ultimo_tercio_ame': ame_att,
            'pases_ultimo_tercio_riv': riv_att,
            'field_tilt (%)': round(ft, 2) if pd.notna(ft) else np.nan,
            'pases_rival_zona_def': riv_def_passes,
            'acciones_def_ame': ame_def_actions,
            'ppda': round(ppda, 2) if pd.notna(ppda) else np.nan
        })

    df_res = pd.DataFrame(benchmark_metrics)
    print(df_res.to_string(index=False))

    # ------------------------------------------------------------------
    # 3. REGLA ESTRICTA DE JUEGO ABIERTO (EXCLUSIVAMENTE PASS_TYPE/PASS_OUTCOME)
    # ------------------------------------------------------------------
    print("\n3. RECONCILIACIÓN ESTRICTA DE PASES EN JUEGO ABIERTO (5 PARTIDOS):")
    print("-" * 65)

    completed_passes = df_b[(df_b['type'] == 'Pass') & (df_b['pass_outcome'].isna()) & (df_b['end_location_x'].notna())].copy()
    
    # Exclusión estricta de reinicios por patrón o tipo
    restarts_patterns = ['From Corner', 'From Free Kick', 'From Throw In', 'From Kick Off', 'From Goal Kick']
    is_restart = completed_passes['play_pattern'].isin(restarts_patterns)
    
    open_play_passes = completed_passes[~is_restart].copy()

    # Algoritmo de pase progresivo
    dist_start = np.sqrt((120 - open_play_passes['location_x'])**2 + (40 - open_play_passes['location_y'])**2)
    dist_end = np.sqrt((120 - open_play_passes['end_location_x'])**2 + (40 - open_play_passes['end_location_y'])**2)

    cond_prog = (
        ((open_play_passes['location_x'] < 40) & (dist_end <= dist_start * 0.70)) |
        ((open_play_passes['location_x'] >= 40) & (open_play_passes['location_x'] < 80) & (dist_end <= dist_start * 0.85)) |
        ((open_play_passes['location_x'] >= 80) & ((dist_end <= dist_start * 0.90) | (open_play_passes['end_location_x'] >= 102)))
    )

    prog_cnt = cond_prog.sum()

    print(f"• Pases completados totales en los 5 partidos: {len(completed_passes):,}")
    print(f"• Pases en Juego Abierto: {len(open_play_passes):,}")
    print(f"• Pases Progresivos Identificados: {prog_cnt:,} ({prog_cnt / max(1, len(open_play_passes)) * 100:.2f}%)")

    # Guardar reporte oficial en JSON
    out_file = PROCESSED_DIR / "audit_benchmark_5_matches_pyarrow_fix.json"
    audit_data = {
        "fase": "2.3 - Benchmark 5 Partidos (PyArrow Fix)",
        "partidos_recuperados": BENCHMARK_IDS,
        "eventos_totales_ muestra": len(df_b),
        "field_tilt_media": round(df_res['field_tilt (%)'].mean(), 2),
        "ppda_media": round(df_res['ppda'].mean(), 2),
        "pases_juego_abierto": len(open_play_passes),
        "pases_progresivos": int(prog_cnt)
    }

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(audit_data, f, indent=4, ensure_ascii=False)

    print("\n==================================================================")
    print(f"✅ BENCHMARK SOLUCIONADO EXITOSAMENTE. REPORTE EN: {out_file.name}")
    print("==================================================================")

if __name__ == "__main__":
    run_pyarrow_benchmark_fix()