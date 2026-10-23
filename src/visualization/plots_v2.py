"""
Módulo de Visualización V2 Elite - Club América ISAC 2026
Dibuja campos reglamentarios con estética Azulcrema/Neón para mapas de tiros, sonares, gamestate y redes de pases.
"""

import matplotlib.pyplot as plt
import matplotlib.patches as patches
import pandas as pd
import numpy as np
from pathlib import Path

# Estilo Azulcrema Elite
BG_COLOR = "#0A192F"
CARD_BG = "#112240"
BORDER_COLOR = "#233554"
YELLOW_AMERICA = "#F4D03F"
CREAM_AMERICA = "#F5E6CC"
RED_AMERICA = "#E74C3C"

plt.style.use("dark_background")

def draw_pitch(ax):
    """Dibuja un campo reglamentario estilo StatsBomb (120x80) con estética oscura."""
    ax.set_facecolor(CARD_BG)
    
    # Líneas de campo
    plt.plot([0, 0, 120, 120, 0], [0, 80, 80, 0, 0], color=BORDER_COLOR, lw=2)
    plt.plot([60, 60], [0, 80], color=BORDER_COLOR, lw=2)
    
    # Áreas
    ax.add_patch(patches.Rectangle((0, 18), 18, 44, fill=False, edgecolor=BORDER_COLOR, lw=1.5))
    ax.add_patch(patches.Rectangle((102, 18), 18, 44, fill=False, edgecolor=BORDER_COLOR, lw=1.5))
    
    # Círculo central
    centre_circle = patches.Circle((60, 40), 10, fill=False, edgecolor=BORDER_COLOR, lw=1.5)
    ax.add_patch(centre_circle)
    
    ax.set_xlim(-5, 125)
    ax.set_ylim(-5, 85)
    ax.axis('off')

def plot_shot_map_v2(df_events, output_path: Path):
    """Genera un mapa de tiros con escala de xG y resultado del remate."""
    shots = df_events[(df_events["type"] == "Shot") & (df_events["is_america_action"])].copy()
    
    fig, ax = plt.subplots(figsize=(10, 6), facecolor=BG_COLOR)
    draw_pitch(ax)
    
    goals = shots[shots["shot_outcome"] == "Goal"]
    no_goals = shots[shots["shot_outcome"] != "Goal"]
    
    # No goles
    ax.scatter(
        no_goals["location_x"], no_goals["location_y"],
        s=no_goals["shot_statsbomb_xg"] * 400 + 20,
        color=CREAM_AMERICA, alpha=0.35, label='Remate Sin Gol', edgecolors='none'
    )
    
    # Goles
    ax.scatter(
        goals["location_x"], goals["location_y"],
        s=goals["shot_statsbomb_xg"] * 500 + 60,
        color=YELLOW_AMERICA, alpha=0.9, label='GOL ANOTADO', edgecolors=RED_AMERICA, linewidth=2
    )
    
    plt.title("Mapa de Tiros & Generación de Ocasiones (xG) · Club América", color="white", fontsize=13, fontweight='bold', pad=15)
    plt.legend(facecolor=CARD_BG, edgecolor=BORDER_COLOR, labelcolor="white", loc="lower center", ncol=2)
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor=BG_COLOR)
    plt.close()

def plot_passing_network_v2(network_data, output_path: Path):
    """Dibuja la red de pases táctica sobre el terreno de juego."""
    fig, ax = plt.subplots(figsize=(10, 6), facecolor=BG_COLOR)
    draw_pitch(ax)
    
    nodes = network_data["nodes"]
    edges = network_data["edges"]
    
    for _, edge in edges.iterrows():
        if edge["pass_count"] > 3:
            p1 = nodes[nodes["player"] == edge["player"]]
            p2 = nodes[nodes["player"] == edge["pass_recipient"]]
            if not p1.empty and not p2.empty:
                x_vals = [p1["x_mean"].values[0], p2["x_mean"].values[0]]
                y_vals = [p1["y_mean"].values[0], p2["y_mean"].values[0]]
                alpha = min(edge["pass_count"] / 15.0, 1.0)
                ax.plot(x_vals, y_vals, color=YELLOW_AMERICA, alpha=alpha, lw=edge["pass_count"]*0.4)
                
    ax.scatter(nodes["x_mean"], nodes["y_mean"], s=nodes["count"]*12, color=YELLOW_AMERICA, edgecolors=RED_AMERICA, zorder=5)
    
    for _, node in nodes.iterrows():
        name_short = str(node["player"]).split()[-1]
        ax.annotate(name_short, (node["x_mean"], node["y_mean"]-3), color="white", fontsize=9, fontweight="bold", ha="center")
        
    plt.title("Estructura de Circuitos & Posicionamiento Promedio", color="white", fontsize=13, fontweight="bold", pad=15)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=300, bbox_inches="tight", facecolor=BG_COLOR)
    plt.close()

def plot_gamestate_v2(df_gamestate, output_path: Path):
    """Genera un gráfico comparativo de comportamiento táctico según el Marcador."""
    fig, ax1 = plt.subplots(figsize=(9, 5), facecolor=BG_COLOR)
    ax1.set_facecolor(CARD_BG)
    
    states = df_gamestate["Gamestate"].tolist()
    ft_vals = df_gamestate["Field_Tilt_%"].tolist()
    ppda_vals = df_gamestate["PPDA"].tolist()
    
    x = np.arange(len(states))
    width = 0.35
    
    ax1.bar(x - width/2, ft_vals, width, label="Dominio Territorial (Field Tilt %)", color=YELLOW_AMERICA)
    ax1.set_ylabel("Dominio Territorial %", color=YELLOW_AMERICA, fontweight="bold")
    ax1.tick_params(axis="y", labelcolor=YELLOW_AMERICA)
    ax1.set_xticks(x)
    ax1.set_xticklabels(states, color="white", fontweight="bold", fontsize=11)
    
    ax2 = ax1.twinx()
    ax2.bar(x + width/2, ppda_vals, width, label="Intensidad Presión (PPDA)", color=RED_AMERICA)
    ax2.set_ylabel("PPDA (Menor = Más Asfixia)", color=RED_AMERICA, fontweight="bold")
    ax2.tick_params(axis="y", labelcolor=RED_AMERICA)
    
    plt.title("Variación Táctica Según el Estado del Marcador (Gamestate)", color="white", fontsize=13, fontweight="bold", pad=15)
    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=300, bbox_inches="tight", facecolor=BG_COLOR)
    plt.close()