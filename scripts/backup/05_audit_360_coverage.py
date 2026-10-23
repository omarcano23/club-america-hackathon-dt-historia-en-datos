"""
Paso 05: Auditoría de Cobertura Real 360 e Integridad de Eventos (G3, G4, G5)
Fase 1.1 - ISAC 2026
"""

from pathlib import Path
import pandas as pd
import numpy as np

DATA_DIR = Path(r"C:\Users\omarc\AI_Projects\Competitions\club-america-isac-2026\data")

def audit_360_coverage_and_integrity():
    print("==================================================================")
    print("📐 AUDITANDO COBERTURA 360 E INTEGRIDAD DE CAMPOS (G3, G4, G5)")
    print("==================================================================\n")

    events_file = DATA_DIR / "processed" / "events_master.csv"
    frames_file = DATA_DIR / "processed" / "frames_360_master.csv"

    if not events_file.exists() or not frames_file.exists():
        print("❌ No se encontraron los archivos procesados en data/processed/")
        return

    # 1. Cargar únicamente las columnas necesarias de events_master.csv para optimizar memoria
    print("📖 Cargando eventos relevantes desde events_master.csv...")
    cols_ev = ['match_id', 'event_id', 'type', 'is_america_action', 'location_x', 'location_y', 'under_pressure', 'play_pattern']
    df_ev = pd.read_csv(events_file, usecols=cols_ev, low_memory=False)
    print(f"✔️ Total de eventos cargados: {len(df_ev):,}")

    # 2. Obtener la lista única de event_ids presentes en 360
    print("📖 Leyendo event_ids únicos en frames_360_master.csv...")
    df_360_ids = pd.read_csv(frames_file, usecols=['event_id'], low_memory=False)
    events_with_360 = set(df_360_ids['event_id'].dropna().unique())
    print(f"✔️ Eventos únicos con fotograma 360 disponible: {len(events_with_360):,}")

    # 3. Marcar presencia de 360 en la tabla de eventos
    df_ev['has_360'] = df_ev['event_id'].isin(events_with_360)

    # 4. Auditoría de Coordenadas fuera de límite o Nulas (G3)
    null_locs = df_ev['location_x'].isna().sum()
    out_of_bounds = len(df_ev[(df_ev['location_x'] < 0) | (df_ev['location_x'] > 120) | (df_ev['location_y'] < 0) | (df_ev['location_y'] > 80)])
    print(f"\n🧪 INTEGRIDAD DE COORDENADAS:")
    print(f"   • Eventos sin coordenada location_x: {null_locs:,} (e.g., eventos de alineación, cambios, etc.)")
    print(f"   • Eventos con coordenadas fuera de rango (0-120, 0-80): {out_of_bounds}")

    # 5. Cobertura 360 específica en PASES (G4)
    df_passes = df_ev[df_ev['type'] == 'Pass'].copy()
    total_passes = len(df_passes)
    passes_with_360 = df_passes['has_360'].sum()
    pct_pass_360 = (passes_with_360 / max(1, total_passes)) * 100

    # Cobertura 360 específica en pases de América
    df_ame_passes = df_passes[df_passes['is_america_action'] == True]
    total_ame_passes = len(df_ame_passes)
    ame_passes_360 = df_ame_passes['has_360'].sum()
    pct_ame_pass_360 = (ame_passes_360 / max(1, total_ame_passes)) * 100

    print(f"\n📐 COBERTURA DE DATOS 360 EN PASES:")
    print(f"   • Pases Totales en el Dataset: {total_passes:,}")
    print(f"   • Pases Totales con Marco 360: {passes_with_360:,} ({pct_pass_360:.2f}%)")
    print(f"   • Pases del América: {total_ame_passes:,}")
    print(f"   • Pases del América con Marco 360: {ame_passes_360:,} ({pct_ame_pass_360:.2f}%)")

    # Cobertura en pases bajo presión
    df_press_passes = df_ame_passes[df_ame_passes['under_pressure'] == True]
    press_360 = df_press_passes['has_360'].sum()
    pct_press_360 = (press_360 / max(1, len(df_press_passes))) * 100
    print(f"   • Pases del América BAJO PRESIÓN con Marco 360: {press_360:,} de {len(df_press_passes):,} ({pct_press_360:.2f}%)")

    print("\n✅ AUDITORÍA DE COBERTURA 360 COMPLETADA.")

if __name__ == "__main__":
    audit_360_coverage_and_integrity()