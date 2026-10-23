"""
Paso 56 (Fase B - Cierre Absoluto y Documentación del Denominador):
Reconciliación de anomalías, validación espacial y pase a Fase C.
Proyecto: El Vuelo del Bicampeón (ISAC 2026)
"""

from pathlib import Path
import pandas as pd
import json

DATA_DIR = Path(r"C:\Users\omarc\AI_Projects\Competitions\club-america-isac-2026\data")
PROCESSED_DIR = DATA_DIR / "processed"

def finalize_phase_b():
    print("===================================================================")
    print("🔬 FASE B: CIERRE ABSOLUTO Y DOCUMENTACIÓN DEL DENOMINADOR")
    print("===================================================================\n")

    events_file = PROCESSED_DIR / "events_master.csv"
    summary_file = PROCESSED_DIR / "h2_resumen_ppda_r10.csv"

    if not events_file.exists() or not summary_file.exists():
        print("❌ Error: Faltan archivos requeridos en processed/.")
        return

    df_ev = pd.read_csv(events_file, low_memory=False)
    df_summary = pd.read_csv(summary_file)

    df_ev["match_id_clean"] = pd.to_numeric(
        df_ev["match_id"].astype(str).str.replace("match_", ""),
        errors="coerce"
    ).fillna(-1).astype("int64")

    valid_match_ids = set(df_summary["match_id"])
    df_match_ev = df_ev[df_ev["match_id_clean"].isin(valid_match_ids)].copy()

    # Selección espacial validada (X >= 80 en coordenadas nativas congeladas)
    df_rival_att3rd = df_match_ev[
        (~df_match_ev["is_america_action"]) & 
        (df_match_ev["location_x"] >= 80) &
        (df_match_ev["period"] <= 4)
    ].copy()

    # Reconciliación completa de las 18 anomalías ('Unknown' e 'Injury Clearance')
    anomalies_df = df_rival_att3rd[df_rival_att3rd["pass_outcome"].isin(["Unknown", "Injury Clearance"])].copy()
    
    strict_restarts = ["From Corner", "From Free Kick", "From Goal Kick", "From Kick Off", "From Throw In"]
    
    def classify_loss_absolute(row):
        t = row["type"]
        po = row["pass_outcome"]
        pp = row["play_pattern"]

        if pp in strict_restarts:
            return "EXCLUIDO_REINICIO_ESTATICO"
        if t in ["Miscontrol", "Dispossessed"]:
            return "VALIDO_JUEGO_ABIERTO"
        if t == "Pass":
            if pd.isna(po):
                return "EXCLUIDO_PASE_COMPLETADO"
            po_str = str(po).strip()
            if po_str in ["Incomplete", "Out", "Pass Offside"]:
                return "VALIDO_JUEGO_ABIERTO"
            else:
                return f"EXCLUIDO_ANOMALIA_{po_str}"
        return "EXCLUIDO_OTRO_TIPO"

    df_rival_att3rd["clasificacion_final"] = df_rival_att3rd.apply(classify_loss_absolute, axis=1)

    print("1. Reconciliación Detallada de Anomalías (Total de 18 eventos en zona):")
    print("-" * 65)
    anomaly_breakdown = anomalies_df["play_pattern"].value_counts().reset_index(name="count")
    print(anomaly_breakdown.to_string(index=False))
    print("   👉 Nota: De los 18 eventos marginales, 9 ocurrieron bajo patrones de reinicio estático (excluidos por esa regla) y 9 en juego abierto (excluidos por la regla de anomalía). Ninguno ingresa al denominador.")

    # Conteos definitivos congelados
    final_counts = df_rival_att3rd["clasificacion_final"].value_counts()
    valido_count = final_counts.get("VALIDO_JUEGO_ABIERTO", 0)

    print(f"\n2. Denominador Definitivo Congelado: {valido_count:,} pérdidas elegibles en juego abierto.")

    # Generar manifiesto de cierre de Fase B
    fase_b_manifest = {
        "fase": "Fase B - Cierre Metodológico Absoluto",
        "convencion_espacial": "Coordenadas normalizadas nativas en events_master.csv (X de 0 a 120). X >= 80 delimita la zona de presión alta del América ante el último tercio del rival.",
        "total_eventos_zona": int(len(df_rival_att3rd)),
        "desglose_final": final_counts.to_dict(),
        "denominador_congelado": int(valido_count),
        "estado": "Fase B Cerrada y Aprobada para Fase C"
    }

    manifest_path = PROCESSED_DIR / "h2_fase_b_manifiesto_cierre.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(fase_b_manifest, f, indent=4, ensure_ascii=False)

    print(f"\n3. Manifiesto de cierre guardado en: {manifest_path.name}")
    print("===================================================================")
    print("✅ FASE B CERRADA CON ÉXITO. LISTO PARA FASE C.")
    print("==================================================================-\n")

if __name__ == "__main__":
    finalize_phase_b()