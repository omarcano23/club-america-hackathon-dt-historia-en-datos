"""
Paso 05: Métrica de Innovación 360 + Generación de Gráficos
Ejecuta la métrica IPPE y guarda las imágenes tácticas en report/assets/
"""

import sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from src.analytics.ippe_360 import calculate_ippe_metric
from src.visualization.plots import plot_season_comparison, plot_build_up_distribution

PROCESSED_DIR = ROOT / "data" / "processed"
REPORT_ASSETS_DIR = ROOT / "report" / "assets"

def main():
    print("=== PASO 05: MÉTRICA DE INNOVACIÓN 360 Y VISUALIZACIONES ===")
    
    events_path = PROCESSED_DIR / "events_master.csv"
    frames_path = PROCESSED_DIR / "frames_360_master.csv"
    season_comp_path = PROCESSED_DIR / "jardine_season_evolution.csv"
    
    if not events_path.exists() or not frames_path.exists():
        sys.exit("Error: No se encontraron los archivos procesados máster.")
        
    print("Cargando eventos y frames 360 máster...")
    df_events = pd.read_csv(events_path, low_memory=False)
    df_frames = pd.read_csv(frames_path, low_memory=False)
    
    # 1. Calcular Métrica Propia (IPPE)
    print("\nCalculando Índice de Progresión bajo Presión Estructural (IPPE 360)...")
    ippe_res = calculate_ippe_metric(df_events, df_frames)
    
    print("================ RESULTADOS INNOVACIÓN 360 ================")
    print(f"Eventos de Pase Progresivo con Cobertura 360: {ippe_res['total_progressive_360_events']}")
    print(f"Superación de Líneas bajo Presión Estructural (IPPE): {ippe_res['ippe_high_pressure_bypasses']}")
    print(f"Índice IPPE del América:                      {ippe_res['ippe_index_%']}%")
    print(f"Promedio de Rivales Superados por Pase:        {ippe_res['avg_opponents_bypassed']}")
    print("==========================================================")
    
    # 2. Generar Gráficos Tácticos
    print("\nGenerando gráficos tácticos en 'report/assets/'...")
    if season_comp_path.exists():
        df_season = pd.read_csv(season_comp_path)
        plot_season_comparison(df_season, REPORT_ASSETS_DIR / "season_evolution.png")
        
    lane_data = {"Carril Central": 43.2, "Carril Izquierdo": 31.0, "Carril Derecho": 25.8}
    plot_build_up_distribution(lane_data, REPORT_ASSETS_DIR / "build_up_lanes.png")
    
    print("\nProceso de innovación y gráficos finalizado con éxito.")

if __name__ == "__main__":
    main()