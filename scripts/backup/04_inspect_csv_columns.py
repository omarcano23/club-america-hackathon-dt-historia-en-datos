"""
Paso 04: Inspección Exacta del Esquema de Columnas de events_master.csv
Fase 1.1 - ISAC 2026
"""

from pathlib import Path
import pandas as pd

DATA_DIR = Path(r"C:\Users\omarc\AI_Projects\Competitions\club-america-isac-2026\data")

def inspect_columns():
    print("==================================================================")
    print("🔬 INSPECCIONANDO LAS 32 COLUMNAS DE events_master.csv")
    print("==================================================================\n")

    events_file = DATA_DIR / "processed" / "events_master.csv"
    if not events_file.exists():
        print(f"❌ No se encontró el archivo {events_file}")
        return

    df_sample = pd.read_csv(events_file, nrows=5, low_memory=False)
    
    print("📋 Lista completa de columnas encontradas:")
    print("-" * 65)
    for idx, col in enumerate(df_sample.columns, 1):
        print(f"{idx:02d}. {col}")

    print("\n🔍 Muestra de los primeros 2 registros:")
    print("-" * 65)
    print(df_sample.head(2).to_dict(orient='records'))

if __name__ == "__main__":
    inspect_columns()