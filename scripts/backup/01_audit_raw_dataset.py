"""
Paso 01: Auditoría de Integridad y Estructura del Dataset
Fase 1.1 - ISAC 2026 (El Vuelo del Bicampeón)
"""

import os
from pathlib import Path
import json
import pandas as pd

# Ruta raíz de datos configurada
DATA_DIR = Path(r"C:\Users\omarc\AI_Projects\Competitions\club-america-isac-2026\data")

def format_bytes(size):
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} TB"

def audit_directory_structure():
    print("==================================================================")
    print("🔍 INICIANDO AUDITORÍA FÍSICA DE ARCHIVOS EN DIRECTORIO DE DATOS")
    print(f"Ruta Objetivo: {DATA_DIR}")
    print("==================================================================\n")

    if not DATA_DIR.exists():
        print(f"❌ ERROR: La ruta especificada no existe: {DATA_DIR}")
        return

    subfolders = ['raw', 'processed', 'synthetic']
    inventory = []

    for subfolder in subfolders:
        folder_path = DATA_DIR / subfolder
        print(f"📁 Inspeccionando subcarpeta: data/{subfolder}/")
        
        if not folder_path.exists():
            print(f"   ⚠️ La subcarpeta '{subfolder}' no existe aún.")
            continue

        files = list(folder_path.rglob("*"))
        file_count = 0
        
        for file_path in files:
            if file_path.is_file():
                file_count += 1
                size_str = format_bytes(file_path.stat().st_size)
                ext = file_path.suffix.lower()
                
                info = {
                    "subfolder": subfolder,
                    "filename": file_path.name,
                    "relative_path": str(file_path.relative_to(DATA_DIR)),
                    "size": size_str,
                    "extension": ext,
                    "rows": "N/A",
                    "columns_sample": []
                }

                # Lectura de muestra según formato para auditar columnas/filas sin saturar memoria
                try:
                    if ext == '.csv':
                        df_sample = pd.read_csv(file_path, nrows=5, low_memory=False)
                        # Contar filas totales rápido
                        with open(file_path, 'rb') as f:
                            num_rows = sum(1 for _ in f) - 1
                        info["rows"] = f"{num_rows:,}"
                        info["columns_sample"] = list(df_sample.columns[:10])
                    elif ext == '.json':
                        with open(file_path, 'r', encoding='utf-8') as f:
                            data_json = json.load(f)
                            if isinstance(data_json, list):
                                info["rows"] = f"{len(data_json):,}"
                                if len(data_json) > 0 and isinstance(data_json[0], dict):
                                    info["columns_sample"] = list(data_json[0].keys())[:10]
                            elif isinstance(data_json, dict):
                                info["rows"] = "1 dict principal"
                                info["columns_sample"] = list(data_json.keys())[:10]
                except Exception as e:
                    info["rows"] = f"Error al leer: {str(e)[:30]}"

                inventory.append(info)
                print(f"   📄 Archivo: {file_path.name} ({size_str}) | Filas est.: {info['rows']}")

        if file_count == 0:
            print(f"   ℹ️ Subcarpeta '{subfolder}' está vacía.")
        print("-" * 60)

    # Generar reporte de inventario en JSON dentro de processed/ audit_summary.json
    summary_path = DATA_DIR / "processed" / "audit_inventory_summary.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(inventory, f, indent=4, ensure_ascii=False)

    print("\n✅ AUDITORÍA INICIAL COMPLETADA.")
    print(f"Reporte de inventario guardado en: {summary_path}")

if __name__ == "__main__":
    audit_directory_structure()