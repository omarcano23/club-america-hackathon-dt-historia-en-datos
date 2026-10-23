"""
Paso 05 V2 Integrado: Ejecución de Gamestate, Redes de Pases, ABP y Gráficos V2
"""

import sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from src.analytics.gamestate import calculate_gamestate_metrics
from src.analytics.passing_networks import calculate_passing_network
from src.analytics.set_pieces import calculate_set_piece_metrics
from src.visualization.plots_v2 import plot_shot_map_v2, plot_passing_network_v2, plot_gamestate_v2

PROCESSED_DIR = ROOT / "data" / "processed"
REPORT_ASSETS_DIR = ROOT / "report" / "assets"

def main():
    print("=== EJECUTANDO MOTOR V2: GAMESTATE, PASSING NETWORKS & ABP ===")
    
    events_path = PROCESSED_DIR / "events_master.csv"
    if not events_path.exists():
        sys.exit("Error: No se encontró 'events_master.csv'")
        
    print("Cargando base máster de eventos...")
    df_events = pd.read_csv(events_path, low_memory=False)
    
    # 1. Marcador / Gamestate
    print("\nCalculando métricas por Estado del Marcador (Gamestate)...")
    df_gs = calculate_gamestate_metrics(df_events)
    print(df_gs.to_string(index=False))
    plot_gamestate_v2(df_gs, REPORT_ASSETS_DIR / "gamestate_v2.png")
    
    # 2. Red de Pases
    print("\nGenerando Red de Pases Táctica...")
    net_data = calculate_passing_network(df_events)
    plot_passing_network_v2(net_data, REPORT_ASSETS_DIR / "passing_network_v2.png")
    
    # 3. Balón Parado (ABP)
    print("\nCalculando efectividad en Balón Parado (ABP)...")
    abp_res = calculate_set_piece_metrics(df_events)
    print(f"  -> ABP: {abp_res['goals_from_abp']} goles anotados desde ABP ({abp_res['xg_from_abp']} xG en {abp_res['shots_from_abp']} tiros).")
    
    # 4. Mapa de Tiros
    plot_shot_map_v2(df_events, REPORT_ASSETS_DIR / "shot_map_v2.png")
    
    print("\nProceso de integración V2 finalizado con éxito.")

if __name__ == "__main__":
    main()