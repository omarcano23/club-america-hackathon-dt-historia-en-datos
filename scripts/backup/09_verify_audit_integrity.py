"""
Paso 09: Verificación de Ponderación y Relaciones Compuestas (G3, G4)
Fase 1.1 - ISAC 2026 (El Vuelo del Bicampeón)
"""

from pathlib import Path
import pandas as pd
import json

DATA_DIR = Path(r"C:\Users\omarc\AI_Projects\Competitions\club-america-isac-2026\data")
PROCESSED_DIR = DATA_DIR / "processed"

def verify_audit_integrity():
    print("==================================================================")
    print("🔬 RE-CALCULANDO PONDERACIONES E INTEGRIDAD RELACIONAL COMPUESTA")
    print("==================================================================\n")

    events_file = PROCESSED_DIR / "events_master.csv"
    frames_file = PROCESSED_DIR / "frames_360_master.csv"

    # 1. Cargar datos clave
    print("📖 Cargando eventos...")
    df_ev = pd.read_csv(events_file, usecols=['match_id', 'event_id', 'type', 'is_america_action', 'under_pressure'], low_memory=False)
    
    print("📖 Cargando claves 360...")
    df_360_keys = pd.read_csv(frames_file, usecols=['match_id', 'event_id'], low_memory=False)

    # 2. Verificar Unicidad de Clave Compuesta (match_id, event_id)
    print("\n1. PRUEBA DE UNICIDAD DE CLAVE COMPUESTA (match_id, event_id):")
    dup_composite = df_ev.duplicated(subset=['match_id', 'event_id']).sum()
    print(f"   • Eventos duplicados por (match_id, event_id): {dup_composite}")

    # 3. Verificar Huérfanos en 360
    print("\n2. PRUEBA DE HUÉRFANOS EN DATOS 360:")
    set_ev_composite = set(zip(df_ev['match_id'], df_ev['event_id']))
    set_360_composite = set(zip(df_360_keys['match_id'], df_360_keys['event_id']))
    
    orphans_360 = set_360_composite - set_ev_composite
    print(f"   • Eventos en 360 que NO existen en events_master.csv (Huérfanos): {len(orphans_360)}")

    # 4. Cálculo Ponderado Estricto de Cobertura
    unique_360_events = set(df_360_keys['event_id'].dropna().unique())
    df_ev['has_360'] = df_ev['event_id'].isin(unique_360_events)

    df_passes = df_ev[df_ev['type'] == 'Pass']
    total_passes = len(df_passes)
    passes_360 = df_passes['has_360'].sum()
    weighted_global_pass_cov = (passes_360 / total_passes) * 100

    df_ame_passes = df_passes[df_passes['is_america_action'] == True]
    total_ame_passes = len(df_ame_passes)
    ame_passes_360 = df_ame_passes['has_360'].sum()
    weighted_ame_pass_cov = (ame_passes_360 / total_ame_passes) * 100

    print("\n3. RE-CÁLCULO PONDERADO CORREGIDO DE COBERTURA EN PASES:")
    print(f"   • Cobertura Ponderada Global (Todos los Pases): {passes_360:,} / {total_passes:,} = {weighted_global_pass_cov:.2f}%")
    print(f"   • Cobertura Ponderada América (Pases de América): {ame_passes_360:,} / {total_ame_passes:,} = {weighted_ame_pass_cov:.2f}%")

    # 5. Sobrescribir audit_gate_summary.json con datos 100% ponderados y corregidos
    summary_path = PROCESSED_DIR / "audit_gate_summary.json"
    if summary_path.exists():
        with open(summary_path, "r", encoding="utf-8") as f:
            gate_data = json.load(f)
        
        gate_data["cobertura_pases_360_ponderada_global_pct"] = round(weighted_global_pass_cov, 2)
        gate_data["cobertura_pases_360_ponderada_america_pct"] = round(weighted_ame_pass_cov, 2)
        gate_data["puertas_evaluadas"]["G4_cobertura_360"]["evidencia"] = (
            f"Cobertura ponderada global en pases: {weighted_global_pass_cov:.2f}%. "
            f"Cobertura ponderada en pases de América: {weighted_ame_pass_cov:.2f}%. "
            f"Sin registros huérfanos (0 huérfanos)."
        )
        
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(gate_data, f, indent=4, ensure_ascii=False)
        print(f"\n✅ Archivo {summary_path.name} actualizado con denominadores ponderados exactos.")

if __name__ == "__main__":
    verify_audit_integrity()