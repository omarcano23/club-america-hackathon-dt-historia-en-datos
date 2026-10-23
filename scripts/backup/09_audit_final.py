
"""
scripts/09_audit_final.py
Fase 6.5: auditoría previa a la entrega.

Lee report/web_data.json y report/index.html.
No modifica los archivos originales.
"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "report"
JSON_PATH = REPORT_DIR / "web_data.json"
HTML_PATH = REPORT_DIR / "index.html"

ISSUES = []
WARNINGS = []
OK = []


def issue(message):
    ISSUES.append(message)


def warn(message):
    WARNINGS.append(message)


def ok(message):
    OK.append(message)


def get_nested(data, dotted_key):
    current = data
    for part in dotted_key.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def audit_json():
    if not JSON_PATH.exists():
        issue(f"No existe el archivo: {JSON_PATH}")
        return None

    try:
        with JSON_PATH.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except json.JSONDecodeError as exc:
        issue(f"El JSON no es válido: {exc}")
        return None

    if not isinstance(data, dict):
        issue("La raíz del JSON debe ser un objeto.")
        return None

    ok("web_data.json se puede leer y contiene un objeto JSON.")

    metadata = data.get("metadata", {})
    if not isinstance(metadata, dict):
        issue("metadata no es un objeto.")
        metadata = {}

    print("\nMETADATOS")
    print(f"  Versión de datos: {metadata.get('version', 'No indicada')}")
    print(
        "  Política editorial: "
        f"{metadata.get('publication_policy_version', 'No indicada')}"
    )
    print(f"  Estado de datos: {metadata.get('data_status', 'No indicado')}")

    policy = data.get("publicacion", {})
    if not isinstance(policy, dict):
        issue("publicacion no es un objeto.")
        policy = {}

    print("\nPOLÍTICA DE PUBLICACIÓN")

    for key, rule in policy.items():
        if not isinstance(rule, dict):
            warn(f"La regla {key} no tiene una estructura de objeto.")
            continue

        visible = rule.get("visible")
        status = rule.get("estado_publicacion", "SIN_ESTADO")
        metric = get_nested(data, key)

        print(f"  {key}: visible={visible}, estado={status}")

        if visible is True and status == "PENDIENTE_VALIDACION":
            issue(
                f"{key}: aparece visible aunque está pendiente de validación."
            )

        if visible is True and status == "PROVISIONAL":
            warn(
                f"{key}: se publica como provisional. "
                "La interfaz debe explicar sus límites."
            )

        if visible is False and metric is not None:
            warn(
                f"{key}: está oculta por política, pero el dato sigue "
                "en el JSON. La interfaz debe respetar la política."
            )

        if visible is True and metric is None:
            issue(
                f"{key}: autorizada para publicación, pero no se encuentra "
                "la métrica en la ruta indicada."
            )

    if not policy:
        warn("No se encontró política editorial en el JSON.")

    # Comprobaciones de consistencia de campos conocidos.
    known_checks = [
        (
            "capitulo_1_identidad.kpis.field_tilt",
            "La política debe mantener oculta esta cifra hasta reconciliarla."
        ),
        (
            "capitulo_1_identidad.kpis.overperformance_gol",
            "La diferencia goles-xG necesita reconciliación."
        ),
        (
            "capitulo_2_progresion.kpis.pases_tercio_medio",
            "La definición espacial y el denominador requieren validación."
        ),
        (
            "capitulo_2_progresion.kpis.ippe_360_completitud",
            "La métrica 360 requiere validación de definición y muestra."
        ),
        (
            "capitulo_4_contexto.gamestate",
            "Los indicadores por estado del marcador siguen pendientes."
        ),
        (
            "capitulo_5_balon_parado.abp_stats",
            "Las estadísticas de balón parado requieren reconciliar el universo."
        ),
    ]

    for key, explanation in known_checks:
        rule = policy.get(key)
        if isinstance(rule, dict) and rule.get("visible") is True:
            issue(f"{key}: {explanation}")

    # Comprobaciones matemáticas básicas, no una validación estadística.
    recovery = data.get("capitulo_3_recuperacion", {}).get("h2_r10", {})
    if isinstance(recovery, dict):
        try:
            high = float(
                str(recovery["tasa_alta_presion"]).replace("%", "").strip()
            )
            low = float(
                str(recovery["tasa_baja_presion"]).replace("%", "").strip()
            )
            difference = float(
                str(recovery["diferencia_pp"])
                .replace("pp", "")
                .replace("+", "")
                .strip()
            )

            calculated = round(high - low, 2)
            if abs(calculated - difference) > 0.02:
                issue(
                    "H2 R10: la diferencia publicada no coincide con "
                    f"las tasas. Diferencia calculada: {calculated} pp."
                )
            else:
                ok(
                    "H2 R10: la diferencia coincide aproximadamente "
                    "con las tasas publicadas."
                )
        except (KeyError, TypeError, ValueError):
            warn(
                "H2 R10: no se pudo comprobar la diferencia con los "
                "campos disponibles."
            )

        try:
            p_value = float(recovery.get("p_value"))
            if not 0 <= p_value <= 1:
                issue("H2 R10: el p-valor está fuera del rango [0, 1].")
            elif p_value >= 0.05:
                warn(
                    "H2 R10: el p-valor no alcanza el umbral convencional "
                    "de 0.05. No presentar el resultado como confirmatorio."
                )
        except (TypeError, ValueError):
            warn("H2 R10: no se pudo comprobar el p-valor.")

        ci = recovery.get("ic_95")
        if isinstance(ci, str) and "[-" in ci and "+" in ci:
            warn(
                "H2 R10: revisar que el intervalo de confianza se muestre "
                "completo y se explique que incluye cero."
            )

    matches_total = metadata.get("matches_total")
    regular_matches = metadata.get("fase_regular_matches")

    if isinstance(matches_total, (int, float)) and isinstance(
        regular_matches, (int, float)
    ):
        if regular_matches > matches_total:
            issue(
                "El número de partidos de fase regular supera "
                "el total de partidos."
            )
        else:
            ok(
                "Los totales de partidos son numéricamente compatibles. "
                "Esto no valida el universo analítico."
            )

    return data


def audit_html(data):
    if not HTML_PATH.exists():
        issue(f"No existe el archivo: {HTML_PATH}")
        return

    html = HTML_PATH.read_text(encoding="utf-8")
    lower_html = html.lower()

    ok("index.html existe y se puede leer.")

    if "<html" not in lower_html or "</html>" not in lower_html:
        issue("El HTML no contiene una estructura HTML completa.")
    else:
        ok("Se encontraron las etiquetas HTML principales.")

    if "web_data.json" not in html:
        issue("El HTML no parece cargar web_data.json.")
    else:
        ok("El HTML referencia web_data.json.")

    if data:
        policy = data.get("publicacion", {})
        visible_keys = [
            key for key, rule in policy.items()
            if isinstance(rule, dict) and rule.get("visible") is True
        ]

        if visible_keys:
            print("\nMÉTRICAS AUTORIZADAS")
            for key in visible_keys:
                print(f"  - {key}")

    # Detectar controles antiguos que no deberían formar parte del diseño.
    obsolete_labels = [
        "RESPALDADO",
        "PROVISIONAL",
        "Todos",
        "Respaldados",
        "Provisionales",
    ]

    for label in obsolete_labels:
        if label in html:
            warn(
                f"El HTML contiene el texto «{label}». "
                "Comprueba que no sea un filtro editorial antiguo."
            )

    if "EL VUELO DEL BICAMPEÓN" in html:
        warn(
            "El título todavía contiene «EL VUELO DEL BICAMPEÓN». "
            "Confirma que siga siendo la decisión editorial deseada."
        )

    if re.search(r"<script\b", html, flags=re.IGNORECASE):
        ok("Se encontraron bloques de JavaScript.")
    else:
        warn("No se encontraron bloques de JavaScript en el HTML.")

    if "console.error" not in html:
        warn(
            "No se detecta console.error en el código fuente. "
            "Los errores de ejecución deberán comprobarse en el navegador."
        )


def print_report():
    print("\n" + "=" * 64)
    print("RESULTADO DE LA AUDITORÍA")
    print("=" * 64)

    print(f"\nCorrectas: {len(OK)}")
    for item in OK:
        print(f"  [OK] {item}")

    print(f"\nAdvertencias: {len(WARNINGS)}")
    for item in WARNINGS:
        print(f"  [REVISAR] {item}")

    print(f"\nProblemas: {len(ISSUES)}")
    for item in ISSUES:
        print(f"  [ERROR] {item}")

    print("\nConclusión:")
    if ISSUES:
        print("  NO LISTO: resolver los problemas antes de la entrega.")
    elif WARNINGS:
        print(
            "  REVISIÓN PENDIENTE: no se detectaron errores críticos "
            "automáticos, pero hay puntos que requieren comprobación."
        )
    else:
        print(
            "  SIN ALERTAS AUTOMÁTICAS. Esto no sustituye la validación "
            "estadística ni las pruebas en navegador."
        )


def main():
    print("AUDITORÍA FINAL · CLUB AMÉRICA EN DATOS")
    print(f"Directorio: {ROOT}")

    data = audit_json()
    audit_html(data)
    print_report()

    # Código de salida útil para automatizar pruebas.
    if ISSUES:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
