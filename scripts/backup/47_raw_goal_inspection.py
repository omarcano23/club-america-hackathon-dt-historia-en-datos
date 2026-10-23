"""
Paso 47: Inspección Bruta y Sin Filtros de Eventos en Partidos Discrepantes
Proyecto: El Vuelo del Bicampeón (ISAC 2026)
"""

from pathlib import Path
import pandas as pd

DATA_DIR = Path(r"C:\Users\omarc\AI_Projects\Competitions\club-america-isac-2026\data")
PROCESSED_DIR = DATA_DIR / "processed"

def run_raw_inspection():
    print("==================================================================")
    print("🔬 INSPECCIÓN BRUTA Y SIN FILTROS (PARTIDOS 3939923 y 3969395)")
    print("==================================================================\n")

    events_file = PROCESSED_DIR / "events_master.csv"
    if not events_file.exists():
        print(f"❌ Error: {events_file} no existe.")
        return

    # Cargar el DataFrame maestro
    df = pd.read_csv(events_file, low_memory=False)
    df["match_id_clean"] = pd.to_numeric(
        df["match_id"].astype(str).str.replace("match_", ""),
        errors="coerce"
    ).fillna(0).astype("int64")

    TARGET_IDS = [3939923, 3969395]

    for match_id in TARGET_IDS:
        print(f"\n{'=' * 80}")
        print(f"MATCH ID: {match_id}")
        print(f"{'=' * 80}")

        m = df[df["match_id_clean"] == match_id].copy()
        if m.empty:
            print("⚠️ No se encontraron filas para este match_id.")
            continue

        # Filtrar periodos 1-4 reglamentarios
        if "period" in m.columns:
            m = m[pd.to_numeric(m["period"], errors="coerce") <= 4]

        # Columnas de interés disponibles en el DataFrame
        potential_cols = [
            "id", "event_id", "index", "period", "timestamp", "minute", "second",
            "type", "team", "player", "possession",
            "shot_outcome", "shot_type",
            "pass_type", "pass_outcome",
            "own_goal", "is_america_action"
        ]
        cols = [c for c in potential_cols if c in m.columns]

        # Si existe timestamp, calcular segundos globales para ordenar o acotar
        if "timestamp" in m.columns and "minute" in m.columns and "second" in m.columns:
            # Mostrar ordenado cronológicamente por periodo, minuto y segundo
            sorted_m = m[cols].sort_values(
                by=[c for c in ["period", "minute", "second", "index"] if c in cols],
                kind="stable"
            )
            # Imprimir eventos donde el resultado sea Goal o tengan relación con autogol/disparo
            goal_filter = sorted_m[
                (sorted_m.get("shot_outcome", pd.Series()) == "Goal") | 
                (sorted_m.get("shot_outcome", pd.Series() ) == "Goal_Penalty") |
                (sorted_m.get("pass_type", pd.Series()) == "Own Goal") |
                (sorted_m.get("type", pd.Series()) == "Own Goal") |
                (sorted_m.get("own_goal", pd.Series()) == True)
            ]
            
            print(f"📋 Total de eventos de gol/autogol detectados en bruto para {match_id}: {len(goal_filter)}")
            if not goal_filter.empty:
                print(goal_filter.to_string(index=False))
            else:
                print("⚠️ Ningún evento cumplió el filtro directo de gol. Mostrando todos los tiros (Shot) del partido:")
                shots_all = sorted_m[sorted_m["type"] == "Shot"]
                print(shots_all.to_string(index=False))
        else:
            print(m[cols].to_string(index=False))

    print("\n==================================================================")
    print("✅ INSPECCIÓN CONCLUIDA.")
    print("==================================================================")

if __name__ == "__main__":
    run_raw_inspection()