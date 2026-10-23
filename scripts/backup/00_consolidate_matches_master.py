"""
Consolidación Definitiva de Tablas Maestras de Partidos
Proyecto: El Vuelo del Bicampeón (ISAC 2026)
"""

from pathlib import Path
import pandas as pd

DATA_DIR = Path(r"C:\Users\omarc\AI_Projects\Competitions\club-america-isac-2026\data")
PROCESSED_DIR = DATA_DIR / "processed"

def consolidate_master_tables():
    print("===================================================================")
    print("🔄 CONSOLIDANDO TABLAS MAESTRAS DE PARTIDOS")
    print("===================================================================\n")

    master_file = PROCESSED_DIR / "fase3_metricas_matches_master.csv"
    metrics_file = PROCESSED_DIR / "fase3_metricas_matches.csv"

    if not master_file.exists() or not metrics_file.exists():
        print("❌ Error: Falta alguno de los archivos CSV base en processed/.")
        return

    df_master = pd.read_csv(master_file)
    df_metrics = pd.read_csv(metrics_file)

    print(f"📊 Registros en master original: {len(df_master)}")
    print(f"📊 Registros en metrics original: {len(df_metrics)}")

    # Limpiar o estandarizar match_id si fuera necesario
    df_master["match_id_clean"] = pd.to_numeric(df_master["match_id"].astype(str).str.replace("match_", ""), errors="coerce")
    df_metrics["match_id_clean"] = pd.to_numeric(df_metrics["match_id"].astype(str).str.replace("match_", ""), errors="coerce")

    # Fusionar ambas tablas conservando el control oficial de master y añadiendo las métricas avanzadas
    # Usamos inner o left join según convenga; un inner asegura que tengamos tanto control de goles como táctica
    df_unified = pd.merge(
        df_master,
        df_metrics.drop(columns=[c for c in ["season", "home_team", "away_team", "is_home", "stage"] if c in df_master.columns], errors="ignore"),
        on=["match_id", "match_id_clean"],
        how="inner"
    )

    # Limpiar columna auxiliar
    df_unified = df_unified.drop(columns=["match_id_clean"])

    # Guardar la tabla unificada definitiva
    unified_path = PROCESSED_DIR / "fase3_matches_master_unificado.csv"
    df_unified.to_csv(unified_path, index=False)

    print(f"\n✅ ¡Consolidación exitosa!")
    print(f"   • Archivo guardado: {unified_path.name}")
    print(f"   • Total de partidos unificados: {len(df_unified)}")
    print(f"   • Columnas totales disponibles ({len(df_unified.columns)}):")
    for idx, col in enumerate(df_unified.columns, 1):
        print(f"     {idx:02d}. {col}")

    print("\n===================================================================")

if __name__ == "__main__":
    consolidate_master_tables()