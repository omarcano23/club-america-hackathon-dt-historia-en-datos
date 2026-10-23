"""
Paso 08: Diagnóstico y Validación de los 5 Archivos de Auditoría
Fase 1.1 - ISAC 2026 (El Vuelo del Bicampeón)
"""

import json
from pathlib import Path
import pandas as pd

DATA_DIR = Path(r"C:\Users\omarc\AI_Projects\Competitions\club-america-isac-2026\data")
PROCESSED_DIR = DATA_DIR / "processed"

def diagnose_audit_files():
    print("==================================================================")
    print("🔍 DIAGNÓSTICO Y VALIDACIÓN DE LOS ARCHIVOS DE AUDITORÍA (FASE 1.1)")
    print("==================================================================\n")

    files_to_check = [
        "audit_match_ids_reconciliation.csv",
        "audit_events_by_match.csv",
        "audit_360_coverage.csv",
        "audit_data_quality.csv",
        "audit_gate_summary.json"
    ]

    # 1. Verificación de existencia física y tamaño
    missing = []
    print("📋 ESTADO DE EXISTENCIA FÍSICA:")
    for fname in files_to_check:
        fpath = PROCESSED_DIR / fname
        if fpath.exists():
            size_kb = fpath.stat().st_size / 1024.0
            print(f"   ✔️ {fname:<38} | {size_kb:.2f} KB")
        else:
            print(f"   ❌ {fname:<38} | FALTANTE")
            missing.append(fname)

    if missing:
        print(f"\n⚠️ ERROR CRÍTICO: Faltan {len(missing)} archivos. Vuelve a ejecutar el Paso 07.")
        return

    # 2. Diagnóstico de Reconciliación de Partidos (Salida 1)
    print("\n------------------------------------------------------------------")
    print("📊 1. ANÁLISIS DE RECONCILIACIÓN DE PARTIDOS (audit_match_ids_reconciliation.csv)")
    print("------------------------------------------------------------------")
    df_rec = pd.read_csv(PROCESSED_DIR / "audit_match_ids_reconciliation.csv")
    
    total_ids = df_rec['match_id'].nunique()
    ids_in_events = df_rec['in_events_csv'].sum()
    ids_in_360 = df_rec['in_360_csv'].sum()
    
    print(f"   • Partidos únicos en catálogo: {total_ids}")
    print(f"   • Partidos confirmados con eventos en CSV: {ids_in_events} ({ids_in_events/total_ids*100:.1f}%)")
    print(f"   • Partidos confirmados con marcos 360 en CSV: {ids_in_360} ({ids_in_360/total_ids*100:.1f}%)")
    
    # 3. Diagnóstico de Completitud de Eventos (Salida 2)
    print("\n------------------------------------------------------------------")
    print("🧪 2. ANÁLISIS DE COMPLETITUD Y ANOMALÍAS (audit_events_by_match.csv)")
    print("------------------------------------------------------------------")
    df_ev_match = pd.read_csv(PROCESSED_DIR / "audit_events_by_match.csv")
    
    min_events = df_ev_match['total_eventos'].min()
    max_events = df_ev_match['total_eventos'].max()
    avg_events = df_ev_match['total_eventos'].mean()
    duplicated_ids = df_ev_match[df_ev_match['total_eventos'] != df_ev_match['eventos_unicos']]
    
    print(f"   • Promedio de eventos por partido: {avg_events:.1f} (Rango: {min_events} a {max_events})")
    print(f"   • Partidos con event_ids duplicados: {len(duplicated_ids)}")

    # 4. Diagnóstico de Cobertura 360 (Salida 3)
    print("\n------------------------------------------------------------------")
    print("📐 3. ANÁLISIS DE COBERTURA 360 DESGLOSADA (audit_360_coverage.csv)")
    print("------------------------------------------------------------------")
    df_cov = pd.read_csv(PROCESSED_DIR / "audit_360_coverage.csv")
    
    # Cobertura promedio en Pases
    pass_cov = df_cov[df_cov['type'] == 'Pass']
    if not pass_cov.empty:
        avg_pass_cov = pass_cov['pct_cobertura'].mean()
        print(f"   • Cobertura promedio en eventos tipo 'Pass': {avg_pass_cov:.2f}%")
        print("   • Muestra de cobertura por temporada y fase:")
        print(pass_cov[['season', 'stage_canonical', 'total_eventos', 'eventos_con_360', 'pct_cobertura']].to_string(index=False))

    # 5. Lectura del Resumen de Puertas (Salida 5)
    print("\n------------------------------------------------------------------")
    print("🏁 4. RESUMEN OFICIAL DE PUERTAS DE AUDITORÍA (audit_gate_summary.json)")
    print("------------------------------------------------------------------")
    with open(PROCESSED_DIR / "audit_gate_summary.json", "r", encoding="utf-8") as f:
        gate_data = json.load(f)

    for gate, details in gate_data.get("puertas_evaluadas", {}).items():
        status = details.get("estado", "Desconocido")
        evidence = details.get("evidencia", "")
        symbol = "✅" if "Aprobada" in status else "⚠️"
        print(f"   {symbol} {gate:<20} | Estado: {status:<24}")
        print(f"      Evidencia: {evidence}")

    print("\n==================================================================")
    print("✅ VALIDACIÓN Y DIAGNÓSTICO FINALIZADOS SINCERAMENTE")
    print("==================================================================")

if __name__ == "__main__":
    diagnose_audit_files()