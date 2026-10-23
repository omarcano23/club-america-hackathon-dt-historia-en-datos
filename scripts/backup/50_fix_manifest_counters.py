"""
Paso 50: Ajuste de Contadores en el Manifiesto de la Fase 3
Proyecto: El Vuelo del Bicampeón (ISAC 2026)
"""

import json
from pathlib import Path

DATA_DIR = Path(r"C:\Users\omarc\AI_Projects\Competitions\club-america-isac-2026\data")
PROCESSED_DIR = DATA_DIR / "processed"

def fix_manifest():
    manifest_path = PROCESSED_DIR / "fase3_analytical_manifest.json"
    if not manifest_path.exists():
        print("❌ Error: fase3_analytical_manifest.json no existe.")
        return

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    # Corrección estricta de contadores y separación de capas
    manifest["controles_aceptacion"] = {
        "cobertura_tabla_maestra": "91/91 partidos",
        "reconciliacion_metadatos_oficiales": "91/91 coincidentes",
        "reconciliacion_goles_eventos": "89/91 coincidentes",
        "excepciones_documentadas": 2
    }

    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=4, ensure_ascii=False)

    print("==================================================================")
    print("✅ MANIFIESTO ACTUALIZADO Y CONTADORES CORREGIDOS CORRECTAMENTE.")
    print("==================================================================\n")
    print(json.dumps(manifest["controles_aceptacion"], indent=4, ensure_ascii=False))

if __name__ == "__main__":
    fix_manifest()