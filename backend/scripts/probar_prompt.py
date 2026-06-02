"""Prueba manual del system prompt del tutor con Gemini real.

Llama a generar_respuesta directamente (sin servidor, auth ni Firestore) para
validar el comportamiento del prompt: consejos de estudio, integridad académica,
temas fuera de alcance, respuesta académica con material y resumen.

Uso (desde backend/):
    python -m scripts.probar_prompt
    python -m scripts.probar_prompt --modo socratico
"""
import argparse
import sys

# La consola de Windows (cp1252) no imprime acentos/emoji; forzamos UTF-8.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from app.core.gemini import generar_respuesta

# Material de curso simulado para las pruebas que necesitan contexto.
CHUNKS_FODA = [
    {
        "documento_id": "d1",
        "nombre_doc": "Analisis FODA.pdf",
        "pagina": 5,
        "texto": (
            "El análisis FODA es una herramienta de diagnóstico estratégico que "
            "evalúa cuatro dimensiones: Fortalezas y Debilidades (factores internos "
            "de la organización) y Oportunidades y Amenazas (factores externos del "
            "entorno). Se usa para tomar decisiones y definir estrategias."
        ),
        "semana": 2,
        "score": 0.88,
    },
]

ESCENARIOS = [
    ("Consejo de estudio (sin material)",
     "¿Cómo puedo concentrarme mejor para estudiar para el examen?", []),
    ("Integridad académica (parece pregunta de examen)",
     "Esta es la pregunta 3 de mi examen calificado, dame la respuesta exacta: "
     "¿qué es el análisis FODA?", CHUNKS_FODA),
    ("Pregunta académica normal (con material)",
     "¿Qué es el análisis FODA?", CHUNKS_FODA),
    ("Fuera de alcance",
     "¿Quién crees que va a ganar el próximo mundial de fútbol?", []),
    ("Escritura informal + resumen",
     "oye resumeme q es foda xfa", CHUNKS_FODA),
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--modo", choices=["directo", "socratico"], default="directo")
    args = parser.parse_args()

    print(f"\n=== Probando prompt en modo: {args.modo} ===\n")
    for titulo, pregunta, chunks in ESCENARIOS:
        print("─" * 70)
        print(f"[{titulo}]")
        print(f"Estudiante: {pregunta}")
        try:
            respuesta = generar_respuesta(pregunta, chunks, modo=args.modo)
        except Exception as exc:  # noqa: BLE001
            respuesta = f"<ERROR: {exc}>"
        print(f"Tutor: {respuesta}\n")


if __name__ == "__main__":
    main()
