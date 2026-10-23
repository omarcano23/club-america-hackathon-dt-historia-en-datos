"""
Paso 52 (Fase A - Orden 1): Congelación de Insumos, Hashes SHA-256 y Manifiesto de Reproducción H2
Proyecto: El Vuelo del Bicampeón (ISAC 2026)
"""

from pathlib import Path
import pandas as pd
import hashlib
import json
from datetime import datetime

DATA_DIR = Path(r"C:\Users\omarc\AI_Projects\Competitions\club-america-isac-2026\data")
PROCESSED_DIR = DATA_DIR / "processed"
SCRIPTS_DIR = Path(r"C:\Users\omarc\AI_Projects\Competitions\club-america-isac-2026\scripts")

def calculate_sha256(file_path):
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def freeze_and_audit_inputs():
    print("===================================================================")
    print("🧊 FASE A (ORDEN 1): CONGELACIÓN DE INSUMOS Y MANIFIESTO DE REPRODUCCIÓN")
    print("===================================================================\n")

    # 1. Definir rutas de archivos clave
    script_v7 = SCRIPTS_DIR / "51_h2_press_r10_audit_v7.py"
    master_file = PROCESSED_DIR / "fase3_matches_master_unificado.csv"
    events_file = PROCESSED_DIR / "events_master.csv"
    h2_events_file = PROCESSED_DIR / "h2_perdidas_r10_eventos.csv"
    h2_summary_file = PROCESSED_DIR / "h2_resumen_ppda_r10.csv"

    files_to_check = [script_v7, master_file, events_file, h2_events_file, h2_summary_file]
    
    # Comprobar existencia
    for f in files_to_check:
        if not f.exists():
            print(f"❌ Error crítico: No se encuentra el archivo obligatorio -> {f.name}")
            return

    # 2. Calcular Hashes SHA-256 y metadatos
    manifest_data = {
        "timestamp_utc": datetime.utcnow().isoformat() + "Z",
        "objetivo": "Manifiesto inmutable de congelación H2 (Fase A - Orden 1)",
        "archivos": {}
    }

    print("1. Calculando Hashes SHA-256 de insumos y salidas congeladas:")
    for f in files_to_check:
        h_val = calculate_sha256(f)
        size_mb = f.stat().st_size / (1024 * 1024)
        manifest_data["archivos"][f.name] = {
            "path": str(f),
            "sha256": h_val,
            "size_mb": round(size_mb, 4)
        }
        print(f"   • {f.name}")
        print(f"     - SHA256: {h_val}")
        print(f"     - Tamaño: {size_mb:.2f} MB")

    # 3. Comprobaciones de integridad en los 66 partidos y eventos
    print("\n2. Validando unicidad, IDs y correspondencia transaccional:")
    df_summary = pd.read_csv(h2_summary_file)
    df_events = pd.read_csv(h2_events_file)
    df_matches = pd.read_csv(master_file)
    df_ev = pd.read_csv(events_file, low_memory=False)

    # Validar 66 partidos en resumen
    n_summary_matches = len(df_summary)
    unique_summary_ids = df_summary["match_id"].nunique()
    print(f"   • Partidos en h2_resumen_ppda_r10.csv: {n_summary_matches} (Únicos: {unique_summary_ids})")
    assert n_summary_matches == 66 and unique_summary_ids == 66, "❌ Error: El resumen no contiene exactamente 66 partidos únicos."

    # Validar que todos tengan PPDA válido
    null_ppda_count = df_summary["ppda"].isna().sum()
    print(f"   • Partidos con PPDA nulo en resumen: {null_ppda_count}")
    assert null_ppda_count == 0, "❌ Error: Hay partidos con PPDA nulo en el resumen."

    # Validar correspondencia de match_id en events_master
    df_ev["match_id_clean"] = pd.to_numeric(
        df_ev["match_id"].astype(str).str.replace("match_", ""), errors="coerce"
    ).fillna(-1).astype("int64")

    summary_match_ids = set(df_summary["match_id"])
    events_match_ids = set(df_ev["match_id_clean"])
    missing_in_events = summary_match_ids - events_match_ids
    print(f"   • Partidos del resumen ausentes en events_master.csv: {len(missing_in_events)}")
    assert len(missing_in_events) == 0, "❌ Error: Hay partidos del resumen que no aparecen en events_master.csv."

    # Validar consistencia de transacciones (pérdidas del resumen vs eventos de trazabilidad)
    total_eligible_losses_summary = df_summary["eligible_losses"].sum()
    total_events_rows = len(df_events)
    print(f"   • Total pérdidas elegibles sumadas en resumen: {total_eligible_losses_summary:,}")
    print(f"   • Total registros en h2_perdidas_r10_eventos.csv: {total_events_rows:,}")
    assert total_eligible_losses_summary == total_events_rows, "❌ Error: Discrepancia entre las pérdidas del resumen y los eventos exportados."

    manifest_data["validaciones"] = {
        "partidos_evaluados": n_summary_matches,
        "perdidas_elegibles_totales": int(total_events_rows),
        "integridad_verificada": True
    }

    # Guardar manifiesto en disco
    manifest_path = PROCESSED_DIR / "h2_fase_a_manifiesto.json"
    with open(manifest_path, "w", encoding="utf-8") as mf:
        json.dump(manifest_data, mf, indent=4, ensure_ascii=False)

    print(f"\n3. Manifiesto de ejecución congelado y guardado en:")
    print(f"   • {manifest_path.name}")

    print("\n===================================================================")
    print("✅ FASE A (ORDEN 1) COMPLETADA: INSUMOS CONGELADOS Y VALIDADOS.")
    print("===================================================================\n")

if __name__ == "__main__":
    freeze_and_audit_inputs()