
"""
Fase 6 — Entregable 6.2-A
Crea el contrato editorial del dashboard El Vuelo del Bicampeón.

Entradas: ninguna.
Salidas:
  report/editorial_contract_6_2.json
  report/editorial_contract_6_2.md

No modifica index.html ni web_data.json.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "report"

CONTRACT = {
    "metadata": {
        "project": "El Vuelo del Bicampeón",
        "phase": "6.2-A",
        "purpose": "Definir reglas editoriales antes de conectar contenido y cifras a la interfaz.",
        "language": "es",
        "status": "BORRADOR_PARA_APROBACION",
        "changes_existing_dashboard": False
    },
    "central_thesis": {
        "title": "Control territorial, progresión y adaptación competitiva",
        "text": (
            "El América de Jardine puede estudiarse como un equipo que busca "
            "instalarse en campo rival, transformar su circulación en progresión "
            "y recuperar el balón mediante presión. Los datos permiten explorar "
            "cómo se relacionan estos mecanismos con el peligro generado y el "
            "comportamiento según el contexto, distinguiendo los patrones "
            "consolidados de las asociaciones aún inciertas."
        )
    },
    "audience": {
        "primary": "Aficionados al fútbol y lectores interesados en entender el juego.",
        "secondary": [
            "Analistas y profesionales del fútbol",
            "Evaluadores del concurso",
            "Lectores interesados en metodología y datos"
        ],
        "editorial_rule": (
            "Explicar primero el significado futbolístico; después, la métrica "
            "y su detalle metodológico."
        )
    },
    "narrative_structure": [
        {
            "id": "capitulo_1",
            "name": "La identidad",
            "question": "¿Dónde se instalaba el América?",
            "purpose": (
                "Explorar el dominio territorial y su evolución sin confundir "
                "presencia en campo rival con generación de ocasiones."
            ),
            "visual_role": "Comparación temporal del dominio territorial y la presión."
        },
        {
            "id": "capitulo_2",
            "name": "La progresión",
            "question": "¿Cómo convertía la circulación en avance?",
            "purpose": (
                "Comparar rutas de progresión y su relación con el avance "
                "hacia zonas peligrosas."
            ),
            "visual_role": "Cancha por carriles, rutas y comparación de resultados."
        },
        {
            "id": "capitulo_3",
            "name": "La recuperación",
            "question": "¿Presionar más se asociaba con recuperar mejor?",
            "purpose": (
                "Examinar la relación entre presión y recuperación, mostrando "
                "la incertidumbre estadística."
            ),
            "visual_role": "Comparación de tasas con intervalo de confianza."
        },
        {
            "id": "capitulo_4",
            "name": "La adaptación",
            "question": "¿Qué cambiaba según el marcador?",
            "purpose": (
                "Describir diferencias de comportamiento al ganar, empatar "
                "o perder sin afirmar causalidad."
            ),
            "visual_role": "Comparaciones por estado del marcador y contexto."
        },
        {
            "id": "capitulo_5",
            "name": "El balón parado",
            "question": "¿Qué amenazas aparecían cuando el juego se detenía?",
            "purpose": (
                "Explorar córners, tiros libres y saques de banda por separado."
            ),
            "visual_role": "Mapas de ejecuciones, destinos y remates."
        }
    ],
    "evidence_statuses": {
        "RESPALDADO": (
            "Definición, universo, denominador y resultado reconciliados "
            "con la fuente de origen."
        ),
        "DESCRIPTIVO": (
            "Resume lo observado en una muestra; no implica causalidad "
            "ni necesariamente generaliza fuera de ella."
        ),
        "PROVISIONAL": (
            "Resultado exploratorio con validaciones pendientes o incertidumbre "
            "que debe explicitarse junto al hallazgo."
        ),
        "NO_EVALUABLE": (
            "La muestra, definición o calidad de los datos no permite responder "
            "la pregunta planteada."
        ),
        "PENDIENTE_DE_VERIFICACION": (
            "No publicar como resultado factual hasta reconciliar su origen."
        )
    },
    "editorial_rules": [
        "No presentar una cifra como validada solo porque aparezca en web_data.json.",
        "Cada afirmación cuantitativa debe enlazarse con una fuente identificable.",
        "Registrar definición, numerador, denominador y universo de cada métrica.",
        "Mostrar intervalos de confianza cuando sean relevantes y estén calculados correctamente.",
        "No describir asociaciones como causas.",
        "Distinguir goles totales, goles sin penalti, xG y npxG.",
        "No comparar métricas si sus universos o definiciones no son compatibles.",
        "Explicar términos técnicos en lenguaje futbolístico en su primera aparición.",
        "No inventar citas, declaraciones, secuencias de juego ni conclusiones tácticas.",
        "Si una cifra no está reconciliada, marcarla como pendiente y no usarla en un titular definitivo."
    ],
    "standard_chapter_layers": [
        "Pregunta futbolística",
        "Hallazgo principal y estado de evidencia",
        "Visualización dominante",
        "Exploración interactiva",
        "Lectura futbolística y límite interpretativo",
        "Metodología y procedencia"
    ],
    "design_principles": {
        "identity": [
            "Identidad visual americanista reconocible",
            "Estética editorial deportiva, no un panel corporativo genérico",
            "Fotografías y recursos oficiales o autorizados"
        ],
        "visual_integrity": [
            "Evitar dobles ejes que sugieran relaciones engañosas",
            "Mantener escalas comparables en las comparaciones",
            "No depender solo del color para comunicar evidencia",
            "Mostrar el tamaño de muestra y la incertidumbre donde corresponda"
        ],
        "interaction": [
            "Cada filtro debe modificar realmente los datos compatibles",
            "Los tooltips deben explicar la métrica y su definición",
            "Las transiciones deben ser breves y respetar movimiento reducido",
            "La interfaz debe funcionar en móvil y con teclado"
        ]
    },
    "publication_gate": [
        "Titular y texto revisados editorialmente",
        "Fuente y universo de la cifra identificados",
        "Definición y denominador reconciliados",
        "Estado de evidencia asignado",
        "Limitaciones visibles para el lector",
        "Ninguna cifra pendiente presentada como confirmada"
    ]
}


def build_markdown(contract):
    lines = [
        "# Contrato editorial — El Vuelo del Bicampeón",
        "",
        f"**Fase:** {contract['metadata']['phase']}",
        f"**Estado:** {contract['metadata']['status']}",
        "",
        "## Tesis central",
        "",
        f"**{contract['central_thesis']['title']}**",
        "",
        contract["central_thesis"]["text"],
        "",
        "## Audiencia y regla editorial",
        "",
        contract["audience"]["primary"],
        "",
        f"> {contract['audience']['editorial_rule']}",
        "",
        "## Los cinco capítulos",
        ""
    ]

    for chapter in contract["narrative_structure"]:
        lines.extend([
            f"### {chapter['id'].replace('_', ' ').title()} — {chapter['name']}",
            "",
            f"**Pregunta:** {chapter['question']}",
            "",
            f"**Propósito:** {chapter['purpose']}",
            "",
            f"**Visual principal:** {chapter['visual_role']}",
            ""
        ])

    lines.extend(["## Estados de evidencia", ""])
    for status, description in contract["evidence_statuses"].items():
        lines.extend([f"- **{status}:** {description}"])

    lines.extend(["", "## Reglas editoriales", ""])
    for rule in contract["editorial_rules"]:
        lines.append(f"- {rule}")

    lines.extend(["", "## Capas estándar de cada capítulo", ""])
    for layer in contract["standard_chapter_layers"]:
        lines.append(f"- {layer}")

    lines.extend(["", "## Puerta de publicación", ""])
    for item in contract["publication_gate"]:
        lines.append(f"- [ ] {item}")

    lines.extend([
        "",
        "---",
        "",
        "Documento generado para revisión. No certifica por sí mismo "
        "la validez de ninguna cifra."
    ])

    return "\n".join(lines) + "\n"


def main():
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    json_path = REPORT_DIR / "editorial_contract_6_2.json"
    md_path = REPORT_DIR / "editorial_contract_6_2.md"

    json_path.write_text(
        json.dumps(CONTRACT, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8"
    )
    md_path.write_text(build_markdown(CONTRACT), encoding="utf-8")

    # Comprobaciones básicas de integridad.
    loaded = json.loads(json_path.read_text(encoding="utf-8"))
    assert len(loaded["narrative_structure"]) == 5
    assert len(loaded["standard_chapter_layers"]) == 6
    assert loaded["metadata"]["changes_existing_dashboard"] is False

    print("Checkpoint 6.2-A generado correctamente.")
    print(f"JSON: {json_path.relative_to(ROOT)}")
    print(f"Markdown: {md_path.relative_to(ROOT)}")
    print("Capítulos: 5 | Capas por capítulo: 6")
    print("HTML y web_data.json: sin modificaciones.")


if __name__ == "__main__":
    main()
