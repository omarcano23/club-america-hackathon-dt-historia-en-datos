"""
Paso 65: Auditoría Rigurosa de Hipótesis H1 (Atracción y Progresión)
- H1a: Secuencias de Posesión (2+ pases centrales -> descarga exterior)
- H1b: Cobertura y Respuesta Observable en Freeze Frames 360
- H1c: Tasa de Progresión a X>=80 e IC 95% Bootstrap por Partido

Proyecto: El Vuelo del Bicampeón (ISAC 2026)
"""

from pathlib import Path
import json
import pandas as pd
import numpy as np

DATA_DIR = Path(r"C:\Users\omarc\AI_Projects\Competitions\club-america-isac-2026\data")
PROCESSED_DIR = DATA_DIR / "processed"

def run_h1_sequence_audit():
    print("===================================================================")
    print("🔬 AUDITORÍA H1 CORREGIDA: SECUENCIAS + BOOTSTRAP POR PARTIDO 95%")
    print("==================================================================-\n")

    events_file = PROCESSED_DIR / "events_master.csv"
    summary_file = PROCESSED_DIR / "h2_resumen_ppda_r10.csv"

    if not events_file.exists():
        print("❌ Error: events_master.csv no existe en processed/.")
        return

    df_ev = pd.read_csv(events_file, low_memory=False)

    # 1. Filtrar solo los 66 partidos válidos de Fase Regular
    valid_match_ids = set()
    if summary_file.exists():
        df_sum = pd.read_csv(summary_file)
        valid_match_ids = set(df_sum["match_id"])

    df_match = df_ev[df_ev["match_id"].isin(valid_match_ids)].copy() if valid_match_ids else df_ev.copy()

    # Pases de América en juego abierto
    passes = df_match[
        (df_match["is_america_action"]) & 
        (df_match["type"] == "Pass") & 
        (df_match["pass_outcome"].isna() | (df_match["pass_outcome"] == "Recovery")) &
        (df_match["play_pattern"].isin(["Regular Play", "From Counter", "From Keeper"]))
    ].copy()

    # Definición de carriles (Y entre 24 y 56 es Central)
    passes["is_central"] = (passes["location_y"] >= 24) & (passes["location_y"] <= 56)
    passes["dest_exterior"] = (passes["end_location_y"] < 24) | (passes["end_location_y"] > 56)

    # 2. Agrupar por Posesión para evaluar H1a
    possessions = []
    
    for (match_id, pos_id), grp in passes.groupby(["match_id", "possession"]):
        grp = grp.sort_values(["minute", "second", "index"])
        
        # Filtro de inicio en campo propio (X <= 60)
        first_pass_x = grp.iloc[0]["location_x"]
        if first_pass_x > 60:
            continue
            
        # Evaluar regla de secuencia: >= 2 pases centrales consecutivos seguidos de descarga exterior
        c_count = 0
        h1a_sequence = False
        reached_last_third = False
        has_shot = False

        for idx, row in grp.iterrows():
            if row["end_location_x"] >= 80:
                reached_last_third = True
                
            if row["is_central"]:
                c_count += 1
            else:
                if c_count >= 2 and row["dest_exterior"]:
                    h1a_sequence = True
                c_count = 0

        # Verificar si la posesión terminó en remate
        pos_events = df_match[(df_match["match_id"] == match_id) & (df_match["possession"] == pos_id)]
        if (pos_events["type"] == "Shot").any():
            has_shot = True

        possessions.append({
            "match_id": match_id,
            "possession": pos_id,
            "is_h1a_seq": h1a_sequence,
            "prog_x80": reached_last_third,
            "has_shot": has_shot
        })

    df_pos = pd.DataFrame(possessions)
    
    total_poss = len(df_pos)
    h1a_poss = df_pos["is_h1a_seq"].sum()
    pct_h1a_pos = (h1a_poss / total_poss * 100) if total_poss > 0 else 0.0

    print("1. EVALUACIÓN H1a (Sobre Posesiones Elegibles de Salida X <= 60):")
    print(f"   • Total de posesiones de salida analizadas: {total_poss:,}")
    print(f"   • Posesiones con secuencia (>=2 pases centrales -> exterior): {h1a_poss:,} ({pct_h1a_pos:.2f}%)")
    print(f"   • Umbral táctico objetivo: > 35.0%")
    print(f"   • Clasificación H1a: {'PATRÓN RECURRENTE' if pct_h1a_pos >= 35.0 else 'TENDENCIA MODERADA / INFERIOR A COTA'}\n")

    # 3. Evaluación H1c con Bootstrap por Partido (95% IC)
    match_stats = []
    for m_id, grp in df_pos.groupby("match_id"):
        seq_grp = grp[grp["is_h1a_seq"]]
        other_grp = grp[~grp["is_h1a_seq"]]
        
        rate_seq = seq_grp["prog_x80"].mean() * 100 if len(seq_grp) > 0 else np.nan
        rate_oth = other_grp["prog_x80"].mean() * 100 if len(other_grp) > 0 else np.nan
        
        match_stats.append({
            "match_id": m_id,
            "rate_seq": rate_seq,
            "rate_oth": rate_oth
        })

    df_m = pd.DataFrame(match_stats).dropna()
    
    mean_seq = df_m["rate_seq"].mean()
    mean_oth = df_m["rate_oth"].mean()
    diff_mean = mean_seq - mean_oth

    # Bootstrap por partido (10,000 réplicas)
    np.random.seed(42)
    boot_diffs = []
    n_matches = len(df_m)
    
    for _ in range(10000):
        sample_indices = np.random.choice(df_m.index, size=n_matches, replace=True)
        sample_df = df_m.loc[sample_indices]
        boot_diffs.append(sample_df["rate_seq"].mean() - sample_df["rate_oth"].mean())

    ci_lower = np.percentile(boot_diffs, 2.5)
    ci_upper = np.percentile(boot_diffs, 97.5)

    print("2. EVALUACIÓN H1c (Progresión Efectiva X >= 80 por Partido + Bootstrap 95%):")
    print(f"   • Tasa promedio en Posesiones Central->Exterior: {mean_seq:.2f}%")
    print(f"   • Tasa promedio en Otras Posesiones de Salida: {mean_oth:.2f}%")
    print(f"   • Diferencia Observada de Medias: {diff_mean:+.2f} pp")
    print(f"   • IC 95% Bootstrap Percentil: [{ci_lower:+.2f} pp, {ci_upper:+.2f} pp]")
    
    is_conclusive = (ci_lower > 0)
    print(f"   • Clasificación H1c: {'VENTAJA ESTADÍSTICAMENTE DEMOSTRADA' if is_conclusive else 'VENTAJA OBSERVADA NO CONCLUYENTE (IC incluye 0)'}\n")

    # 4. Auditoría de Cobertura H1b (360)
    passes_360 = passes[passes["has_360"] == True] if "has_360" in passes.columns else passes
    print("3. COBERTURA H1b (Frames 360 Espaciales):")
    print(f"   • Pases de salida con fotograma 360 utilizable: {len(passes_360):,}")
    print(f"   • Nota metodológica: Los frames 360 son muestras discretas por evento. Se documentará como limitación la imposibilidad de medir la trayectoria continua de desplazamiento rival.\n")

    # Guardar reporte JSON
    h1_final_report = {
        "h1a_posesiones": {
            "total_posesiones_salida": total_poss,
            "posesiones_secuencia_h1a": int(h1a_poss),
            "porcentaje_ocurrencia": round(pct_h1a_pos, 2)
        },
        "h1c_bootstrap_95": {
            "tasa_secuencia_central_ext_pct": round(mean_seq, 2),
            "tasa_otras_secuencias_pct": round(mean_oth, 2),
            "diferencia_pp": round(diff_mean, 2),
            "ic_95_lower_pp": round(ci_lower, 2),
            "ic_95_upper_pp": round(ci_upper, 2),
            "es_concluyente": bool(is_conclusive)
        }
    }

    out_file = PROCESSED_DIR / "h1_evaluacion_secuencias_bootstrap.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(h1_final_report, f, indent=4, ensure_ascii=False)

    print(f"✅ Resultados exportados a: {out_file.name}")
    print("===================================================================")

if __name__ == "__main__":
    run_h1_sequence_audit()