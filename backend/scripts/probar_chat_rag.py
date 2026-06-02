"""Prueba manual del flujo RAG completo contra Firestore real (solo lectura).

Replica el pipeline del router de chat: reescritura -> recuperar_chunks ->
fallback de semana (ignorar_semana) -> aviso -> Gemini. Sirve para validar en
local cosas como "resume la semana 4" o el fallback cuando la semana no tiene
material, usando los documentos reales del proyecto.

Uso (desde backend/):
    python -m scripts.probar_chat_rag --curso exYMhyEI13ZdAAGQVW4O
    python -m scripts.probar_chat_rag --curso <id> --modo socratico
"""
import argparse
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from app.config import settings
from app.core.firebase import init_firebase
from app.core.firestore_client import get_db
from app.core.gemini import (
    es_consulta_de_estudio,
    generar_respuesta,
    reescribir_consulta,
)
from app.core.rag import detectar_semana, recuperar_chunks
from app.routers.chat import (
    _aviso_semana_sin_material,
    _chunks_son_debiles,
    _respuesta_sin_material_semana,
    _semanas_disponibles,
)

CURSO_DEFAULT = "exYMhyEI13ZdAAGQVW4O"

PREGUNTAS = [
    "Hazme un resumen de lo que vimos en la semana 4",
    "¿Qué vimos en la semana 7?",
    "Dame consejos para concentrarme mejor antes del examen",
]


def responder(curso_id: str, pregunta: str, db, modo: str):
    consulta = reescribir_consulta(pregunta, [])
    chunks = recuperar_chunks(curso_id, consulta, db)

    if es_consulta_de_estudio(pregunta) and _chunks_son_debiles(chunks):
        chunks = []

    semana = detectar_semana(pregunta)

    aviso = ""
    if semana is not None and not chunks:
        chunks = recuperar_chunks(curso_id, consulta, db, ignorar_semana=True)
        if chunks:
            aviso = _aviso_semana_sin_material(semana, chunks)

    if semana is not None and not chunks:
        return _respuesta_sin_material_semana(
            semana, _semanas_disponibles(curso_id, db)
        ), chunks, semana

    respuesta = generar_respuesta(pregunta, chunks, modo=modo)
    return aviso + respuesta, chunks, semana


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--curso", default=CURSO_DEFAULT)
    parser.add_argument("--modo", choices=["directo", "socratico"], default="directo")
    args = parser.parse_args()

    if not init_firebase():
        print("No se pudo inicializar Firebase. Revisa credenciales en .env.")
        return
    db = get_db()

    print(f"\n=== Flujo RAG (backend={settings.rag_backend}, modo={args.modo}) ===")
    print(f"Curso: {args.curso}\n")
    for pregunta in PREGUNTAS:
        print("─" * 70)
        print(f"Estudiante: {pregunta}")
        try:
            respuesta, chunks, semana = responder(args.curso, pregunta, db, args.modo)
        except Exception as exc:  # noqa: BLE001
            print(f"<ERROR: {exc}>\n")
            continue
        fuentes = ", ".join(
            f"{c.get('nombre_doc', '?')}(sem={c.get('semana')}, score={c.get('score', 0):.2f})"
            for c in chunks
        ) or "—"
        print(f"semana detectada: {semana} | chunks: {len(chunks)} [{fuentes}]")
        print(f"Tutor: {respuesta}\n")


if __name__ == "__main__":
    main()
