"""
Paso 63 (Corregido - Reconstrucción de Tiempos y Validación R10):
Reconstrucción de marcas temporales reales desde events_master.csv,
cierre efectivo de ventanas para VENTANA_AGOTADA, y auditoría de reinicios.

Proyecto: El Vuelo del Bicampeón (ISAC 2026)
"""

from pathlib import Path
import json
import pandas as pd
import numpy as np

DATA_DIR = Path(r"C:\Users\omarc\AI_Projects\Competitions\club-america-isac-2026\data")
PROCESSED_DIR = DATA_DIR / "processed"

def parse_event_time_sec(ev_row):
    """
    Calcula los segundos transcurridos dentro del período a partir de los
    campos reales del evento (minute, second, timestamp).
    """
    period = int(ev_row.get("period", 1))
    minute = float(ev_row.get("minute", 0.0))
    second = float(ev_row.get("second", 0.0))
    
    # Si existe timestamp string (e.g. '00:15:32.450')
    ts_str = str(ev_row.get("timestamp", "")).strip()
    if ts_str and ts_str != "nan" and ":" in ts_str:
        try:
            parts = ts_str.split(":")
            m = float(parts[1])
            s = float(parts[2])
            return m * 60.0 + s
        except Exception:
            pass
            
    return minute * 60.0 + second

def run_semantic_audit_and_time_reconstruction():
    print("===================================================================")
    print("🔬 AUDITORÍA SEMÁNTICA Y RECONSTRUCCIÓN TEMPORAL ($R_{10}$)")
    print("==================================================================-\n")

    events_file = PROCESSED_DIR / "events_master.csv"
    trans_file = PROCESSED_DIR / "h2_corregido_transacciones.csv"
    if not trans_file.exists():
        trans_file = PROCESSED_DIR / "h2_perdidas_r10_eventos.csv"

    if not events_file.exists() or not trans_file.exists():
        print("❌ Error: No se encontraron los archivos máster o de transacciones requeridos.")
        return

    df_ev = pd.read_csv(events_file, low_memory=False)
    df_tr = pd.read_csv(trans_file, low_memory=False)

    loss_key = "loss_event_id" if "loss_event_id" in df_tr.columns else "event_id"

    # Indexar events_master por (match_id, event_id)
    df_ev_indexed = df_ev.set_index(["match_id", "event_id"], drop=False)

    audit_rows = []
    excepciones_rows = []

    used_recovery_ids = set()
    duplicate_recoveries = 0
    invalid_recovery_source = 0
    not_america_recoveries = 0

    invalid_delta_t_count = 0
    zero_time_loss_count = 0
    reinicio_detectado_count = 0

    strict_restarts = ["From Corner", "From Free Kick", "From Goal Kick", "From Kick Off", "From Throw In"]

    for _, row in df_tr.iterrows():
        m_id = row["match_id"]
        l_id = row[loss_key]

        # 1. Recuperar el evento padre en events_master
        if (m_id, l_id) in df_ev_indexed.index:
            p_ev = df_ev_indexed.loc[(m_id, l_id)]
            if isinstance(p_ev, pd.DataFrame):
                p_ev = p_ev.iloc[0]

            p_type = p_ev.get("type", "UNKNOWN")
            p_outcome = str(p_ev.get("pass_outcome", "")).strip()
            p_pattern = str(p_ev.get("play_pattern", "UNKNOWN")).strip()
            loc_x = float(p_ev.get("location_x", -1.0))
            loc_y = float(p_ev.get("location_y", -1.0))
            period = int(p_ev.get("period", -1))

            # Reconstrucción del sello de tiempo de la pérdida
            loss_time = parse_event_time_sec(p_ev)
            anomalia = "NINGUNA"
        else:
            anomalia = "ERROR_EVENTO_PADRE_NO_ENCONTRADO"
            p_type, p_outcome, p_pattern, loc_x, loc_y, period = "UNKNOWN", "UNKNOWN", "UNKNOWN", -1.0, -1.0, -1
            loss_time = -1.0

        if loss_time == 0.0 and period == 1 and float(p_ev.get("second", 0.0)) == 0.0:
            # Es válido si realmente ocurrió en el segundo 0 del partido
            pass
        elif loss_time < 0:
            zero_time_loss_count += 1
            anomalia = "ALERTA_TIEMPO_PERDIDA_INVALIDO"

        # 2. Inclusiones de reinicios no deseados
        is_reinicio = p_pattern in strict_restarts
        if is_reinicio:
            reinicio_detectado_count += 1
            anomalia = f"ALERTA_REINICIO_INCLUIDO_{p_pattern.replace(' ', '_')}"

        outcome_val = str(row.get("outcome_type", row.get("terminal_outcome", "UNKNOWN"))).strip()
        rec_id = str(row.get("recovery_event_id", "N/A")).strip()

        # 3. Determinación de terminal_timestamp y delta_t
        if outcome_val == "RECUPERACION_EFECTIVA" and rec_id not in ["N/A", "nan", "None", ""]:
            if rec_id in used_recovery_ids:
                duplicate_recoveries += 1
                anomalia = "ALERTA_RECUPERACION_DUPLICADA"
            else:
                used_recovery_ids.add(rec_id)

            if (m_id, rec_id) in df_ev_indexed.index:
                rec_ev = df_ev_indexed.loc[(m_id, rec_id)]
                if isinstance(rec_ev, pd.DataFrame):
                    rec_ev = rec_ev.iloc[0]

                if not bool(rec_ev.get("is_america_action", False)):
                    not_america_recoveries += 1
                    anomalia = "ALERTA_RECUPERACION_NO_ES_DE_AMERICA"

                term_time = parse_event_time_sec(rec_ev)
                delta_t = term_time - loss_time
            else:
                invalid_recovery_source += 1
                anomalia = "ALERTA_RECUPERACION_ID_NO_EXISTE_EN_MASTER"
                term_time = loss_time
                delta_t = -1.0
        elif outcome_val == "VENTANA_AGOTADA":
            # Para ventana agotada, el tiempo terminal es estrictamente loss_time + 10.0s
            delta_t = 10.0
            term_time = loss_time + 10.0
        else:
            # Para otros desenlaces intermedios (interrupción, salida, remate)
            elapsed_raw = float(row.get("elapsed_seconds", np.nan))
            if not pd.isna(elapsed_raw) and elapsed_raw >= 0:
                delta_t = elapsed_raw
                term_time = loss_time + delta_t
            else:
                delta_t = 0.0
                term_time = loss_time

        if pd.isna(delta_t) or delta_t < 0.0 or delta_t > 10.00:
            invalid_delta_t_count += 1
            anomalia = f"ALERTA_VENTANA_TEMPORAL_INVALIDA_{delta_t:.2f}s"

        if anomalia != "NINGUNA":
            excepciones_rows.append({
                "match_id": m_id,
                "event_id": l_id,
                "motivo_excepcion": anomalia,
                "loss_timestamp_sec": loss_time,
                "terminal_timestamp_sec": term_time,
                "delta_t_sec": delta_t,
                "recovery_event_id": rec_id
            })

        audit_rows.append({
            "match_id": m_id,
            "event_id": l_id,
            "period": period,
            "type": p_type,
            "pass_outcome": p_outcome if p_outcome not in ["nan", "None", ""] else "N/A",
            "location_x": loc_x,
            "location_y": loc_y,
            "criterio_espacial": "SALIDA_RIVAL_X_LE_40" if loc_x <= 40 else "FUERA_DE_ZONA",
            "play_pattern": p_pattern,
            "loss_timestamp_sec": round(loss_time, 2),
            "terminal_timestamp_sec": round(term_time, 2),
            "delta_t_sec": round(delta_t, 2),
            "terminal_outcome": outcome_val,
            "recovery_event_id": rec_id if rec_id not in ["nan", "None"] else "N/A",
            "anomalia_detectada": anomalia
        })

    df_audit = pd.DataFrame(audit_rows)
    df_excep = pd.DataFrame(excepciones_rows)

    # 4. Exportaciones
    csv_out = PROCESSED_DIR / "h2_auditoria_semantica_C.csv"
    df_audit.to_csv(csv_out, index=False)

    csv_excep_out = PROCESSED_DIR / "h2_excepciones_semanticas_C.csv"
    df_excep.to_csv(csv_excep_out, index=False)

    keys_c = set(zip(df_audit["match_id"], df_audit["event_id"]))

    json_out = PROCESSED_DIR / "h2_validacion_semantica_C.json"
    validation_summary = {
        "integridad_claves_C": {
            "total_filas": len(df_audit),
            "claves_unicas": len(keys_c),
            "claves_duplicadas": len(df_audit) - len(keys_c),
            "claves_nulas": int(df_audit["event_id"].isna().sum())
        },
        "ventana_temporal_R10": {
            "cero_desenlaces_fuera_de_rango": bool(invalid_delta_t_count == 0),
            "conteo_desenlaces_invalidos_delta_t": invalid_delta_t_count,
            "tiempos_perdida_invalidos_cero": zero_time_loss_count
        },
        "recuperaciones": {
            "total_recuperaciones_efectivas": int((df_audit["terminal_outcome"] == "RECUPERACION_EFECTIVA").sum()),
            "referencias_unicas_usadas": len(used_recovery_ids),
            "recuperaciones_duplicadas": duplicate_recoveries,
            "recuperaciones_no_existentes_en_master": invalid_recovery_source,
            "recuperaciones_que_no_pertenecen_a_america": not_america_recoveries
        },
        "coordenadas_y_reinicios": {
            "eventos_con_X_le_40": int((df_audit["location_x"] <= 40).sum()),
            "filtro_espacial_100_pct_cumplido": bool((df_audit["location_x"] <= 40).all()),
            "reinicios_estaticos_detectados": reinicio_detectado_count
        },
        "excepciones": {
            "total_excepciones": len(df_excep),
            "desglose_por_regla": df_audit["anomalia_detectada"].value_counts().to_dict()
        }
    }

    with open(json_out, "w", encoding="utf-8") as f:
        json.dump(validation_summary, f, indent=4, ensure_ascii=False)

    print(f"✅ Transacciones procesadas: {len(df_audit)}")
    print(f"📁 CSV Auditoría: {csv_out.name}")
    print(f"📁 CSV Excepciones: {csv_excep_out.name} ({len(df_excep)} filas)")
    print(f"📁 JSON de Validación Generado: {json_out.name}\n")
    print("===================================================================")

if __name__ == "__main__":
    run_semantic_audit_and_time_reconstruction()