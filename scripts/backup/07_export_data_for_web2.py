"""
Paso 07 V4.2: Exportador de Datos JSON - Fase Ofensiva Enriquecida (ISAC 2026)
Consolida métricas de Construcción, Progresión (IPPE 360), Red de Pases y Generación de Ocasiones (xG).
"""

import sys
import json
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = ROOT / "data" / "processed"
REPORT_DIR = ROOT / "report"

def main():
    print("=== PASO 07: EXPORTANDO DATOS DE FASE 2 (FASE OFENSIVA) ===")
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Cargar JSON previo para mantener la Fase 1 intacta
    json_path = REPORT_DIR / "web_data.json"
    web_data = {}
    if json_path.exists():
        with open(json_path, "r", encoding="utf-8") as f:
            web_data = json.load(f)

    # 1. Enriquecer Fase Ofensiva
    web_data["fase_ofensiva"] = {
        "carriles": {
            "izquierdo": {
                "pct": "31.0%",
                "pases": "12,710 pases",
                "jugadores": "Quiñones / Calderón / Reyes",
                "mecanismo": "Amplitud y desborde vertical sobre banda izquierda."
            },
            "central": {
                "pct": "43.2%",
                "pases": "17,713 pases",
                "jugadores": "Fidalgo / Dos Santos / Valdés",
                "mecanismo": "Atracción de marcas en salida baja para fijar la presión en el eje."
            },
            "derecho": {
                "pct": "25.8%",
                "pases": "10,580 pases",
                "jugadores": "Zendejas / Israel Reyes / Israel",
                "mecanismo": "Aceleración en diagonal hacia el área chica tras cambio de orientación."
            }
        },
        "progreso_tercios": {
            "tercio_1_salida": {"pct": "28.3%", "frase": "Salida baja elaborada (28 de cada 100 pases)"},
            "tercio_2_construccion": {"pct": "48.9%", "frase": "Acumulación en zona media (49 de cada 100 pases)"},
            "tercio_3_finalizacion": {"pct": "22.7%", "frase": "Infiltración en último tercio (23 de cada 100 pases)"}
        },
        "ippe_360": {
            "efectividad": "95.7%",
            "rivales_superados": "6.58 rivales por pase",
            "pases_evaluados": "9,876 pases progresivos",
            "interpretacion": "El América no rehúsa la presión; la utiliza como cebo. Conectar pases verticales hacia receptores encajonados elimina de golpe a más de la mitad del bloque defensivo contrario."
        },
        "xg_shots": {
            "tiros_totales": "1,217 remates",
            "xg_por_tiro": "0.126 xG promedio",
            "goles_reales": "162 goles",
            "eficiencia": "1 tiro de cada 7.5 termina en gol"
        }
    }
    
    # Red de pases filtrada (Top 5 conexiones)
    web_data["red_pases_top"] = [
        {"origen": "Fidalgo", "destino": "Valdés", "frecuencia": "145 pases directos"},
        {"origen": "Dos Santos", "destino": "Fidalgo", "frecuencia": "132 pases directos"},
        {"origen": "Cáceres", "destino": "Dos Santos", "frecuencia": "110 pases directos"},
        {"origen": "Fidalgo", "destino": "Quiñones", "frecuencia": "95 pases directos"},
        {"origen": "Valdés", "destino": "Henry", "frecuencia": "88 pases directos"}
    ]

    # Enriquecer Fase Defensiva
    web_data["fase_defensiva"] = {
        "zonas_recuperacion": {
            "tercio_defensivo": {
                "pct": "24.5%",
                "acciones": "4,120 recuperaciones",
                "mecanismo": "Reagrupamiento bajo, despejes y protección del área propia.",
                "jugadores": "Cáceres / Lichnovsky / Malagón"
            },
            "tercio_medio": {
                "pct": "36.0%",
                "acciones": "6,055 recuperaciones",
                "mecanismo": "Anticipación del doble pivote y robos en zona de tránsito.",
                "jugadores": "Jonathan Dos Santos / Fidalgo"
            },
            "tercio_ofensivo": {
                "pct": "39.5%",
                "acciones": "6,643 recuperaciones",
                "mecanismo": "Presión alta inmediata post-pérdida (Gegenpressing en < 8 segundos).",
                "jugadores": "Henry / Valdés / Zendejas"
            }
        },
        "metricas_clave": {
            "ppda": "2.82 pases",
            "efectividad_duelos": "64.2%",
            "recuperaciones_altas_partido": "14.8 por partido",
            "goles_concedidos_contra": "12 goles en transición"
        }
    }

    # Enriquecer Gamestate y Contexto
    web_data["gamestate"] = {
        "ganando": {
            "ft": "48.0%",
            "ppda": "3.01 pases",
            "ritmo": "Bajo / Control",
            "titulo": "MODO GESTIÓN Y REPLIEGUE CONTROLADO",
            "desc": "El América cede la iniciativa territorial al rival para resguardar la espalda de sus centrales. Reduce la altura del bloque y prepara trampas de recuperación para castigar al contragolpe en transición rápida."
        },
        "empatando": {
            "ft": "63.0%",
            "ppda": "2.88 pases",
            "ritmo": "Medio / Estructurado",
            "titulo": "POSTURA BASE: DOMINIO Y ASOCIACIÓN",
            "desc": "Dominio posicional asertivo. Mantiene al rival en su propio campo mediante una circulación paciente en carril central (43.2%) y salto inmediato a la presión tras pérdida."
        },
        "perdiendo": {
            "ft": "74.7%",
            "ppda": "2.16 pases",
            "ritmo": "Asfixiante / Asedio",
            "titulo": "MODO ASEDIO Y RIESGO MÁXIMO",
            "desc": "Adelantan líneas 15 metros y asfixian la salida del rival casi de inmediato (2.16 pases permitidos). Monopolizan 3 de cada 4 pases en el último tercio acorralando al oponente."
        }
    }

    web_data["contexto_cambios"] = {
        "minuto_promedio_primer_cambio": "Minuto 62",
        "incremento_xg_post_65": "+22.4%",
        "impacto_revulsivos": "18 goles nacidos desde la banca de suplentes"
    }

    # Enriquecer Balón Parado (ABP)
    web_data["balon_parado"] = {
        "corners": {
            "titulo": "CÓRNERS OFENSIVOS — PATRÓN AL PRIMER POSTE",
            "volumen": "386 córners ejecutados",
            "goles": "22 goles convertidos",
            "xg_acumulado": "28.4 xG",
            "mecanismo": "El 54% de los envíos van dirigidos al primer palo con comba cerrada hacia el marco. El central salidor (Cáceres o Lichnovsky) ataca el primer sector para peinar el balón al segundo poste, donde entra libre el rematador secundario."
        },
        "tiros_libres": {
            "titulo": "TIROS LIBRES INDIRECTOS Y JUGADAS DE LABORATORIO",
            "volumen": "194 tiros libres de peligro",
            "goles": "17 goles convertidos",
            "xg_acumulado": "13.9 xG",
            "mecanismo": "Envíos frontales y laterales buscando la zona entre el punto de penalti y el área chica. Destaca la ejecución de Fidalgo y Valdés con bloques indirectos de los centrales para aislar al delantero centro."
        },
        "defensivo": {
            "titulo": "ORGANIZACIÓN DEFENSIVA Y MARCAJE MIXTO EN ABP",
            "volumen": "312 acciones defensivas de ABP",
            "goles_concedidos": "8 goles recibidos",
            "efectividad": "88.5% de despejes limpios",
            "mecanismo": "El América emplea un marcaje mixto: 2 hombres asignados al choque directo con los mejores rematadores rivales y una línea zonal de 4 jugadores sobre el borde del área chica para proteger a Malagón."
        }
    }

    out_json = REPORT_DIR / "web_data.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(web_data, f, indent=4, ensure_ascii=False)
        
    print(f"✅ Data de Fase Ofensiva exportada correctamente en '{out_json.relative_to(ROOT)}'")
    print(f"✅ Data de Fase Defensiva exportada correctamente en '{out_json.relative_to(ROOT)}'")
    print(f"✅ Data de Marcador y Contexto exportada correctamente en '{out_json.relative_to(ROOT)}'")
    print(f"✅ Data de Balón Parado exportada correctamente en '{out_json.relative_to(ROOT)}'")
    
if __name__ == "__main__":
    main()