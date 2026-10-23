"""
Paso 03: Cálculo de Métricas Tácticas Generales - Proyecto Club América ISAC 2026
Aplica los módulos de analytics sobre la Capa Processed y genera un reporte inicial de KPIs.
"""

import sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from src.analytics.offensive import calculate_progressive_passes, calculate_build_up_patterns, calculate_xg_summary
from src.analytics.defensive import calculate_ppda, calculate_field_tilt, calculate_high_recoveries

PROCESSED_DIR = ROOT / "data" / "processed"

def main():
    print("=== PASO 03: CÁLCULO DE MÉTRICAS TÁCTICAS (ANDRÉ JARDINE) ===")
    
    events_path = PROCESSED_DIR / "events_master.csv"
    if not events_path.exists():
        sys.exit("Error: No se encontró 'events_master.csv' en data/processed/")
        
    print("Cargando 'events_master.csv'...")
    df_events = pd.read_csv(events_path, low_memory=False)
    print(f"Total de eventos cargados: {len(df_events)}")
    
    # 1. Métricas Ofensivas
    prog_passes = calculate_progressive_passes(df_events)
    build_up = calculate_build_up_patterns(df_events)
    xg_data = calculate_xg_summary(df_events)
    
    # 2. Métricas Defensivas
    ppda = calculate_ppda(df_events)
    field_tilt = calculate_field_tilt(df_events)
    recoveries = calculate_high_recoveries(df_events)
    
    print("\n================ RESULTADOS TÁCTICOS GENERALES ================")
    print(f"Pases Progresivos Totales del América:  {len(prog_passes[prog_passes['is_progressive']])}")
    print(f"Distribución de Salida por Carril:       {build_up}")
    print(f"xG Total Generado:                       {xg_data['total_xg']} xG ({xg_data['goals']} goles en {xg_data['total_shots']} tiros)")
    print(f"xG Promedio por Tiro:                    {xg_data['xg_per_shot']}")
    print(f"PPDA (Intensidad de Presión):            {ppda}")
    print(f"Field Tilt (Dominio Territorial):         {field_tilt}%")
    print(f"Recuperaciones Altas en Campo Rival:     {recoveries['high_recoveries']} ({recoveries['high_recovery_pct']}%)")
    print("===============================================================")
    
    # Guardar resumen en CSV
    summary_df = pd.DataFrame([{
        "metric_group": "Offensive", "metric_name": "Progressive Passes", "value": len(prog_passes[prog_passes['is_progressive']])},
        {"metric_group": "Offensive", "metric_name": "Build Up Left Lane %", "value": build_up.get("Izquierdo", 0)},
        {"metric_group": "Offensive", "metric_name": "Build Up Center Lane %", "value": build_up.get("Central", 0)},
        {"metric_group": "Offensive", "metric_name": "Build Up Right Lane %", "value": build_up.get("Derecho", 0)},
        {"metric_group": "Offensive", "metric_name": "Total xG", "value": xg_data['total_xg']},
        {"metric_group": "Offensive", "metric_name": "xG per Shot", "value": xg_data['xg_per_shot']},
        {"metric_group": "Defensive", "metric_name": "PPDA", "value": ppda},
        {"metric_group": "Defensive", "metric_name": "Field Tilt %", "value": field_tilt},
        {"metric_group": "Defensive", "metric_name": "High Recoveries", "value": recoveries['high_recoveries']},
        {"metric_group": "Defensive", "metric_name": "High Recovery %", "value": recoveries['high_recovery_pct']}
    ])
    
    out_path = PROCESSED_DIR / "jardine_tactical_summary.csv"
    summary_df.to_csv(out_path, index=False)
    print(f"\nResumen de KPIs tácticos guardado en '{out_path.relative_to(ROOT)}'")

if __name__ == "__main__":
    main()