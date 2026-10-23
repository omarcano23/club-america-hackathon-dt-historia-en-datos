"""
Paso 66 (Corregido): Auditoría de Hipótesis H3 (Balón Parado en Liguilla vs Fase Regular)
Cálculo de remates, xG acumulado, xG por remate y contraste estadístico.

Proyecto: El Vuelo del Bicampeón (ISAC 2026)
"""

from pathlib import Path
import json
import pandas as pd
import numpy as np
from scipy import stats

DATA_DIR = Path(r"C:\Users\omarc\AI_Projects\Competitions\club-america-isac-2026\data")
PROCESSED_DIR = DATA_DIR / "processed"

def run_h3_set_pieces_audit():
    print("===================================================================")
    print("🔬 AUDITORÍA H3: BALÓN PARADO EN LIGUILLA VS TEMPORADA REGULAR")
    print("==================================================================-\n")

    events_file = PROCESSED_DIR / "events_master.csv"
    matches_file = PROCESSED_DIR / "fase3_metricas_matches_master.csv"

    if not events_file.exists() or not matches_file.exists():
        print("❌ Error: Faltan archivos maestros en data/processed/.")
        return

    df_ev = pd.read_csv(events_file, low_memory=False)
    df_m = pd.read_csv(matches_file)

    # 1. Normalización de match_id para un cruce perfecto
    df_ev["match_id_clean"] = pd.to_numeric(
        df_ev["match_id"].astype(str).str.replace("match_", ""),
        errors="coerce"
    ).fillna(-1).astype("int64")

    df_m["match_id_clean"] = pd.to_numeric(
        df_m["match_id"].astype(str).str.replace("match_", ""),
        errors="coerce"
    ).fillna(-1).astype("int64")

    # Mapeo de fase canónica
    stage_map = dict(zip(df_m["match_id_clean"], df_m["stage"]))
    df_ev["stage_canonical"] = df_ev["match_id_clean"].map(stage_map)
    
    # Asignación de etiqueta de fase
    df_ev["fase"] = np.where(df_ev["stage_canonical"] == "Liguilla", "Liguilla", "Fase Regular")

    # 2. Filtrar remates del América a Balón Parado (máximo 3 pases en secuencia)
    abp_patterns = ["From Corner", "From Free Kick", "From Throw In"]
    
    shots_abp = df_ev[
        (df_ev["is_america_action"]) & 
        (df_ev["type"] == "Shot") & 
        (df_ev["play_pattern"].isin(abp_patterns)) &
        (df_ev["period"] <= 4)
    ].copy()

    # H3a y H3b: Resumen por categoría y fase
    summary = []
    
    for (pattern, fase), grp in shots_abp.groupby(["play_pattern", "fase"]):
        n_shots = len(grp)
        tot_xg = grp["shot_statsbomb_xg"].sum()
        xg_per_shot = tot_xg / n_shots if n_shots > 0 else 0.0
        
        summary.append({
            "tipo_abp": pattern,
            "fase": fase,
            "remates": n_shots,
            "xg_acumulado": round(float(tot_xg), 2),
            "xg_por_remate": round(float(xg_per_shot), 4)
        })

    df_summary = pd.DataFrame(summary)
    print("1. RESUMEN DE AMENAZA POR CATEGORÍA DE ABP (H3a & H3b):")
    print(df_summary.to_string(index=False))
    print("\n" + "-"*65 + "\n")

    # H3c: Inferencia Estadística - ABP Oficial (Córners + Tiros Libres)
    official_abp = shots_abp[shots_abp["play_pattern"].isin(["From Corner", "From Free Kick"])].copy()
    
    reg_shots = official_abp[official_abp["fase"] == "Fase Regular"]["shot_statsbomb_xg"].dropna()
    lig_shots = official_abp[official_abp["fase"] == "Liguilla"]["shot_statsbomb_xg"].dropna()

    n_reg = len(reg_shots)
    n_lig = len(lig_shots)

    print("2. INFERENCIA ESTADÍSTICA (LIGUILLA VS FASE REGULAR EN ABP OFICIAL - H3c):")
    print(f"   • Remates Evaluados: {n_reg + n_lig:,} ({n_reg} en Fase Regular, {n_lig} en Liguilla)")

    if n_reg > 0 and n_lig > 0:
        u_stat, p_val = stats.mannwhitneyu(reg_shots, lig_shots, alternative="two-sided")

        # Bootstrap para diferencia de xG promedio por tiro (10,000 iteraciones)
        np.random.seed(42)
        boot_diffs = []
        
        for _ in range(10000):
            samp_reg = np.random.choice(reg_shots, size=n_reg, replace=True)
            samp_lig = np.random.choice(lig_shots, size=n_lig, replace=True)
            boot_diffs.append(np.mean(samp_lig) - np.mean(samp_reg))

        ci_lower = np.percentile(boot_diffs, 2.5)
        ci_upper = np.percentile(boot_diffs, 97.5)

        print(f"   • Calidad Media Fase Regular: {reg_shots.mean():.4f} xG/tiro")
        print(f"   • Calidad Media Liguilla:     {lig_shots.mean():.4f} xG/tiro")
        print(f"   • Diferencia Absoluta:       {(lig_shots.mean() - reg_shots.mean()):+.4f} xG/tiro")
        print(f"   • IC 95% Bootstrap:          [{ci_lower:+.4f} xG, {ci_upper:+.4f} xG]")
        print(f"   • Mann-Whitney U p-value:    {p_val:.4f}")
        
        estado = "DIFERENCIA SIGNIFICATIVA" if p_val < 0.05 else "PATRÓN ESTABLE (Sin diferencia significativa)"
        print(f"   • Estado H3c: {estado}\n")

        inferencia_res = {
            "remates_regular": n_reg,
            "remates_liguilla": n_lig,
            "xg_promedio_regular": round(float(reg_shots.mean()), 4),
            "xg_promedio_liguilla": round(float(lig_shots.mean()), 4),
            "diferencia_xg": round(float(lig_shots.mean() - reg_shots.mean()), 4),
            "ic_95_lower": round(float(ci_lower), 4),
            "ic_95_upper": round(float(ci_upper), 4),
            "p_value": round(float(p_val), 4),
            "estado": estado
        }
    else:
        print("   ⚠️ Alerta: Muestra de Liguilla o Fase Regular con 0 observaciones. Comparación no evaluable.")
        inferencia_res = {
            "remates_regular": n_reg,
            "remates_liguilla": n_lig,
            "estado": "NO_EVALUABLE_MUESTRA_VACIA"
        }

    # Guardar reporte JSON
    out_json = PROCESSED_DIR / "h3_abp_liguilla_audit.json"
    h3_report = {
        "desglose_abp": summary,
        "inferencia_oficial": inferencia_res
    }

    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(h3_report, f, indent=4, ensure_ascii=False)

    print(f"✅ Artefacto H3 exportado exitosamente a: {out_json.name}")
    print("===================================================================")

if __name__ == "__main__":
    run_h3_set_pieces_audit()