"""
Módulo de Visualización Táctica - Club América ISAC 2026
Genera mapas de tiro (xG), sonares de pases y distribuciones de presión.
"""

import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
from pathlib import Path

# Estilo visual alineado al Club América (Azulcrema)
CLUB_AMERICA_YELLOW = "#F4D03F"
CLUB_AMERICA_BLUE = "#1B2631"
ACCENT_RED = "#CB4335"

plt.style.use("dark_background")

def plot_season_comparison(df_season, output_path: Path):
    """Genera gráfico de barras comparativo de xG y PPDA entre temporadas."""
    fig, ax1 = plt.subplots(figsize=(10, 6))
    
    seasons = df_season["Temporada"].tolist()
    xg_vals = df_season["xG_Total"].tolist()
    ppda_vals = df_season["PPDA"].tolist()
    
    x = np.arange(len(seasons))
    width = 0.35
    
    # Barras de xG
    rects1 = ax1.bar(x - width/2, xg_vals, width, label='xG Total Generado', color=CLUB_AMERICA_YELLOW)
    ax1.set_ylabel('xG Acumulado', color=CLUB_AMERICA_YELLOW, fontsize=12, fontweight='bold')
    ax1.tick_params(axis='y', labelcolor=CLUB_AMERICA_YELLOW)
    ax1.set_xticks(x)
    ax1.set_xticklabels(seasons, fontsize=11, fontweight='bold')
    
    # Eje secundario para PPDA
    ax2 = ax1.twinx()
    rects2 = ax2.bar(x + width/2, ppda_vals, width, label='PPDA (Intensidad Presión)', color=ACCENT_RED)
    ax2.set_ylabel('PPDA (Menor = Más Presión)', color=ACCENT_RED, fontsize=12, fontweight='bold')
    ax2.tick_params(axis='y', labelcolor=ACCENT_RED)
    
    plt.title('Evolución Táctica: André Jardine (2023/24 vs 2024/25)', fontsize=14, fontweight='bold', pad=15)
    fig.tight_layout()
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"  -> Gráfico guardado en '{output_path.name}'")

def plot_build_up_distribution(lane_dict, output_path: Path):
    """Genera gráfico de rosquilla con la distribución de pases por carril."""
    labels = list(lane_dict.keys())
    values = list(lane_dict.values())
    colors = [CLUB_AMERICA_BLUE, CLUB_AMERICA_YELLOW, ACCENT_RED]
    
    fig, ax = plt.subplots(figsize=(7, 7))
    wedges, texts, autotexts = ax.pie(
        values, labels=labels, autopct='%1.1f%%',
        startangle=90, colors=colors, textprops=dict(color="w", fontweight='bold')
    )
    
    # Anillo central (Donut)
    centre_circle = plt.Circle((0,0), 0.70, fc='black')
    fig.gca().add_artist(centre_circle)
    
    ax.set_title("Zona de Salida de Balón por Carril (% Pases)", fontsize=13, fontweight='bold')
    plt.tight_layout()
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"  -> Gráfico guardado en '{output_path.name}'")