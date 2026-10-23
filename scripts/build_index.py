# -*- coding: utf-8 -*-
"""Genera index.html = plantilla.html + datos de los 91 partidos.
Uso:  python build_index.py [ruta_csv]
Edita textos, colores y animaciones en plantilla.html; vuelve a correr este script."""
import sys, json, pandas as pd
from pathlib import Path

CSV = sys.argv[1] if len(sys.argv) > 1 else "data\\processed\\fase3_matches_master_unificado.csv"
AQUI = Path(__file__).parent

def fase(stage):
    if stage in ("Apertura", "Clausura"): return "Fase regular"
    if stage.startswith("Play-offs"): return "Play-In"
    return "Liguilla"

num = lambda v: None if pd.isna(v) else round(float(v), 3)
d = pd.read_csv(CSV)
# [temporada, fase, field_tilt, ppda, xg_ame, xg_rival, goles_ame, goles_rival, match_id]
rows = [[str(r.season).replace("/", "-"), fase(r.stage), num(r.field_tilt_pct), num(r.ppda),
         num(r.ame_xg), num(r.riv_xg), int(r.goles_oficiales_ame),
         int(r.goles_oficiales_rival), int(r.match_id)] for r in d.itertuples()]

html = (
    Path(r"C:\Users\omarc\AI_Projects\Competitions\club-america-isac-2026\report\plantilla.html")
    .read_text(encoding="utf-8")
    .replace("__ROWS__", json.dumps(rows))
)