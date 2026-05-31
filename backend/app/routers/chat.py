"""
Chat con el tutor RAG — endpoints de conversación (RF-13..RF-18).
Flujo: pregunta → embedding → top-k chunks → Gemini → respuesta con citas.
"""
import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from firebase_admin import firestore

from app.config import settings
from app.core.access import verificar_acceso_curso
from app.core.auth import get_current_user
from app.core.firestore_client import get_db
from app.core.gemini import (
    es_rendicion,
    generar_respuesta,
    generar_respuesta_stream,
    reescribir_consulta,
)
from app.core.rag import recuperar_chunks
from app.models.mensaje import (
    ChatRequest,
    ChatResponse,
    ChunkCitado,
    ConversacionOut,
    CursoAnalyticsResponse,
    FeedbackRequest,
    FeedbackResponse,
    MensajeOut,
)

# Cuántos turnos previos de la conversación se envían a Gemini como memoria.
HISTORIAL_MAX_TURNOS = 6

router = APIRouter(tags=["chat"])


def _curso_docente_o_403(curso_id: str, uid: str, db) -> dict:
    curso, usuario = verificar_acceso_curso(curso_id, uid, db)
    if usuario.get("rol") != "docente" or curso.get("docente_id") != uid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo el docente dueno puede ver la analitica del curso.",
        )
    return curso


def _sse_event(event: str, data: dict) -> str:
    payload = json.dumps(data, ensure_ascii=False)
    return f"event: {event}\ndata: {payload}\n\n"


def _chunks_citados(chunks: list[dict]) -> list[dict]:
    return [
        {
            "documento_id": c["documento_id"],
            "nombre_doc": c["nombre_doc"],
            "pagina": c["pagina"],
            "fragmento": c["texto"][:200],
        }
        for c in chunks
    ]


def _titulo_desde_pregunta(pregunta: str | None) -> str:
    """Genera un título corto para la conversación a partir de la primera pregunta."""
    texto = (pregunta or "").strip().replace("\n", " ")
    if not texto:
        return "Nueva conversación"
    return texto[:60] + ("…" if len(texto) > 60 else "")


def _resolver_conversacion(
    curso_id: str, uid: str, conv_id: str | None, db, pregunta: str | None = None
) -> tuple[str, bool]:
    """Devuelve (conversacion_id, es_nueva). Crea la conversación si no existe."""
    if conv_id:
        conv_ref = db.collection("conversaciones").document(conv_id)
        conv_doc = conv_ref.get()
        if not conv_doc.exists:
            conv_id = None
        else:
            conv_data = conv_doc.to_dict() or {}
            if conv_data.get("usuario_id") != uid or conv_data.get("curso_id") != curso_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="No tienes acceso a esta conversacion.",
                )

    if not conv_id:
        _, conv_ref = db.collection("conversaciones").add({
            "curso_id": curso_id,
            "usuario_id": uid,
            "titulo": _titulo_desde_pregunta(pregunta),
            "creado_en": firestore.SERVER_TIMESTAMP,
            "actualizado_en": firestore.SERVER_TIMESTAMP,
        })
        return conv_ref.id, True

    conv_ref.update({"actualizado_en": firestore.SERVER_TIMESTAMP})
    return conv_id, False


def _historial_conversacion(conv_id: str, db, limite: int = HISTORIAL_MAX_TURNOS) -> list[dict]:
    """Recupera los últimos `limite` turnos de la conversación, ordenados
    cronológicamente, para dárselos a Gemini como memoria del diálogo.
    """
    mensajes = db.collection("mensajes").where("conversacion_id", "==", conv_id).stream()
    items: list[tuple[float, dict]] = []
    for m in mensajes:
        data = m.to_dict() or {}
        created = data.get("creado_en")
        ts = created.timestamp() if hasattr(created, "timestamp") else 0.0
        items.append((ts, {
            "pregunta": data.get("pregunta", ""),
            "respuesta": data.get("respuesta", ""),
        }))
    items.sort(key=lambda x: x[0])
    return [turno for _, turno in items[-limite:]]


def _chunks_fallback_historial(conv_id: str, db) -> list[dict]:
    """Recupera los chunks_usados del mensaje más reciente de la conversación
    para usarlos cuando la nueva búsqueda no encontró material relevante.
    Los fragmentos guardados son truncados a 200 chars pero sirven de contexto.
    """
    msgs = list(
        db.collection("mensajes").where("conversacion_id", "==", conv_id).stream()
    )
    if not msgs:
        return []
    items = []
    for m in msgs:
        data = m.to_dict() or {}
        ts = data.get("creado_en")
        t = ts.timestamp() if hasattr(ts, "timestamp") else 0.0
        items.append((t, data))
    items.sort(key=lambda x: x[0])
    ultimo = items[-1][1]
    return [
        {
            "documento_id": c.get("documento_id", ""),
            "nombre_doc": c.get("nombre_doc", ""),
            "pagina": c.get("pagina", 1),
            "texto": c.get("fragmento", c.get("texto", "")),
            "score": 0.0,
        }
        for c in ultimo.get("chunks_usados", [])
    ]


def _flags_rag(chunks: list[dict], modo: str, pregunta: str) -> tuple[bool, bool]:
    """Devuelve (rendicion, contexto_debil).
    rendicion: el estudiante se rindió en modo socrático.
    contexto_debil: el mejor score del RAG está por debajo del umbral de confianza.
    """
    rendicion = modo == "socratico" and es_rendicion(pregunta)
    if not chunks:
        return rendicion, False
    score_max = max(c.get("score", 0.0) for c in chunks)
    contexto_debil = score_max < settings.rag_score_confianza
    return rendicion, contexto_debil


@router.post(
    "/cursos/{curso_id}/chat",
    response_model=ChatResponse,
    summary="Enviar pregunta al tutor RAG (RF-13..RF-17)",
)
def chat_con_tutor(
    curso_id: str,
    body: ChatRequest,
    claims: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """
    Pipeline de chat:
    1. Verifica acceso al curso.
    2. Recupera chunks relevantes via RAG.
    3. Genera respuesta con Gemini Flash.
    4. Crea o actualiza la conversación en Firestore.
    5. Persiste el mensaje y retorna la respuesta con citas.
    """
    uid = claims["uid"]
    verificar_acceso_curso(curso_id, uid, db)

    # ── 1. Resolver conversación (necesaria para recuperar la memoria) ────────
    conv_id, es_nueva = _resolver_conversacion(
        curso_id, uid, body.conversacion_id, db, body.pregunta
    )
    historial = [] if es_nueva else _historial_conversacion(conv_id, db)

    # ── 2. RAG: recuperar chunks relevantes ──────────────────────────────────
    consulta_rag = reescribir_consulta(body.pregunta, historial)
    chunks = recuperar_chunks(curso_id, consulta_rag, db)

    # Fallback: si la búsqueda no trajo nada y hay historial, reutilizamos los
    # chunks del turno anterior (mismo tema, evita el "no está en el material").
    if not chunks and not es_nueva:
        chunks = _chunks_fallback_historial(conv_id, db)

    rendicion, contexto_debil = _flags_rag(chunks, body.modo, body.pregunta)

    # ── 3. Generar respuesta con Gemini (con memoria del diálogo) ────────────
    respuesta = generar_respuesta(
        body.pregunta, chunks, body.modo, historial, rendicion, contexto_debil
    )

    # ── 4. Guardar mensaje ────────────────────────────────────────────────────
    ahora = datetime.now(timezone.utc)
    chunks_citados = [
        {
            "documento_id": c["documento_id"],
            "nombre_doc": c["nombre_doc"],
            "pagina": c["pagina"],
            "fragmento": c["texto"][:200],
        }
        for c in chunks
    ]

    _, msg_ref = db.collection("mensajes").add({
        "conversacion_id": conv_id,
        "curso_id": curso_id,
        "usuario_id": uid,
        "pregunta": body.pregunta,
        "respuesta": respuesta,
        "modo": body.modo,
        "chunks_usados": chunks_citados,
        "creado_en": firestore.SERVER_TIMESTAMP,
    })

    return ChatResponse(
        respuesta=respuesta,
        conversacion_id=conv_id,
        mensaje_id=msg_ref.id,
        modo=body.modo,
        chunks_usados=[ChunkCitado(**c) for c in chunks_citados],
        creado_en=ahora,
    )


@router.post(
    "/cursos/{curso_id}/chat/stream",
    summary="Enviar pregunta al tutor RAG con streaming real",
)
def chat_con_tutor_stream(
    curso_id: str,
    body: ChatRequest,
    claims: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    uid = claims["uid"]
    verificar_acceso_curso(curso_id, uid, db)
    conv_id, es_nueva = _resolver_conversacion(
        curso_id, uid, body.conversacion_id, db, body.pregunta
    )
    historial = [] if es_nueva else _historial_conversacion(conv_id, db)

    def event_stream():
        respuesta_partes: list[str] = []
        chunks_citados: list[dict] = []
        try:
            yield _sse_event("status", {"stage": "retrieving"})
            consulta_rag = reescribir_consulta(body.pregunta, historial)
            chunks = recuperar_chunks(curso_id, consulta_rag, db)

            if not chunks and not es_nueva:
                chunks = _chunks_fallback_historial(conv_id, db)

            rendicion, contexto_debil = _flags_rag(chunks, body.modo, body.pregunta)
            chunks_citados = _chunks_citados(chunks)
            yield _sse_event("meta", {
                "conversacion_id": conv_id,
                "modo": body.modo,
                "chunks_usados": chunks_citados,
            })

            yield _sse_event("status", {"stage": "generating"})
            for delta in generar_respuesta_stream(
                body.pregunta, chunks, body.modo, historial, rendicion, contexto_debil
            ):
                respuesta_partes.append(delta)
                yield _sse_event("delta", {"text": delta})

            respuesta = "".join(respuesta_partes).strip()
            if not respuesta:
                respuesta = (
                    "No pude generar una respuesta completa en este intento. "
                    "Intenta reformular tu consulta de forma mas especifica."
                )
                yield _sse_event("delta", {"text": respuesta})

            ahora = datetime.now(timezone.utc)
            _, msg_ref = db.collection("mensajes").add({
                "conversacion_id": conv_id,
                "curso_id": curso_id,
                "usuario_id": uid,
                "pregunta": body.pregunta,
                "respuesta": respuesta,
                "modo": body.modo,
                "chunks_usados": chunks_citados,
                "creado_en": firestore.SERVER_TIMESTAMP,
            })
            yield _sse_event("done", {
                "respuesta": respuesta,
                "conversacion_id": conv_id,
                "mensaje_id": msg_ref.id,
                "modo": body.modo,
                "chunks_usados": chunks_citados,
                "creado_en": ahora.isoformat(),
            })
        except Exception as exc:
            yield _sse_event("error", {
                "detail": "No se pudo completar el streaming de la respuesta.",
                "message": str(exc),
            })

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get(
    "/cursos/{curso_id}/chat/historial",
    response_model=list[MensajeOut],
    summary="Historial de mensajes del usuario en el curso (RF-18)",
)
def historial_chat(
    curso_id: str,
    conversacion_id: str | None = None,
    claims: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Retorna los mensajes del usuario en el curso, ordenados cronológicamente.
    Si se indica `conversacion_id`, devuelve solo los mensajes de esa conversación.
    """
    uid = claims["uid"]
    verificar_acceso_curso(curso_id, uid, db)

    if conversacion_id:
        mensajes_stream = (
            db.collection("mensajes")
            .where("conversacion_id", "==", conversacion_id)
            .stream()
        )
    else:
        mensajes_stream = (
            db.collection("mensajes")
            .where("curso_id", "==", curso_id)
            .where("usuario_id", "==", uid)
            .stream()
        )

    result = []
    for m in mensajes_stream:
        data = m.to_dict()
        # Cuando se filtra por conversación, asegurar que el mensaje sea del usuario.
        if conversacion_id and data.get("usuario_id") != uid:
            continue
        created = data.get("creado_en")
        if hasattr(created, "timestamp"):
            created = datetime.fromtimestamp(created.timestamp(), tz=timezone.utc)
        else:
            created = datetime.now(timezone.utc)

        result.append(MensajeOut(
            id=m.id,
            pregunta=data.get("pregunta", ""),
            respuesta=data.get("respuesta", ""),
            modo=data.get("modo", "directo"),
            chunks_usados=[ChunkCitado(**c) for c in data.get("chunks_usados", [])],
            creado_en=created,
            feedback_valor=data.get("feedback_valor"),
            feedback_comentario=data.get("feedback_comentario"),
        ))

    return sorted(result, key=lambda x: x.creado_en)


@router.get(
    "/cursos/{curso_id}/conversaciones",
    response_model=list[ConversacionOut],
    summary="Lista las conversaciones del usuario en el curso",
)
def listar_conversaciones(
    curso_id: str,
    claims: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Conversaciones del usuario en el curso, de la más reciente a la más antigua."""
    uid = claims["uid"]
    verificar_acceso_curso(curso_id, uid, db)

    convs_stream = (
        db.collection("conversaciones")
        .where("curso_id", "==", curso_id)
        .where("usuario_id", "==", uid)
        .stream()
    )

    result = []
    for c in convs_stream:
        data = c.to_dict() or {}
        actualizado = data.get("actualizado_en") or data.get("creado_en")
        if hasattr(actualizado, "timestamp"):
            actualizado = datetime.fromtimestamp(actualizado.timestamp(), tz=timezone.utc)
        else:
            actualizado = datetime.now(timezone.utc)

        result.append(ConversacionOut(
            id=c.id,
            titulo=data.get("titulo") or "Conversación",
            actualizado_en=actualizado,
        ))

    return sorted(result, key=lambda x: x.actualizado_en, reverse=True)


@router.patch(
    "/cursos/{curso_id}/chat/mensajes/{mensaje_id}/feedback",
    response_model=FeedbackResponse,
    summary="Registrar feedback de una respuesta del tutor",
)
def registrar_feedback(
    curso_id: str,
    mensaje_id: str,
    body: FeedbackRequest,
    claims: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    uid = claims["uid"]
    verificar_acceso_curso(curso_id, uid, db)

    msg_ref = db.collection("mensajes").document(mensaje_id)
    msg_doc = msg_ref.get()
    if not msg_doc.exists:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mensaje no encontrado.")

    data = msg_doc.to_dict() or {}
    if data.get("curso_id") != curso_id or data.get("usuario_id") != uid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes acceso a este mensaje.",
        )

    comentario = body.comentario.strip() if body.comentario else None
    msg_ref.update({
        "feedback_valor": body.valor,
        "feedback_comentario": comentario,
        "feedback_actualizado_en": firestore.SERVER_TIMESTAMP,
    })
    return FeedbackResponse(
        mensaje_id=mensaje_id,
        feedback_valor=body.valor,
        feedback_comentario=comentario,
    )


@router.get(
    "/cursos/{curso_id}/analytics",
    response_model=CursoAnalyticsResponse,
    summary="Analitica basica del curso para docentes",
)
def analytics_curso(
    curso_id: str,
    claims: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    uid = claims["uid"]
    _curso_docente_o_403(curso_id, uid, db)

    mensajes = list(db.collection("mensajes").where("curso_id", "==", curso_id).stream())
    conversaciones = list(db.collection("conversaciones").where("curso_id", "==", curso_id).stream())
    documentos = list(db.collection("documentos").where("curso_id", "==", curso_id).stream())
    chunks = list(db.collection("chunks").where("curso_id", "==", curso_id).stream())
    matriculas = list(db.collection("matriculas").where("curso_id", "==", curso_id).stream())
    quizzes = list(db.collection("quizzes").where("curso_id", "==", curso_id).stream())
    intentos = list(db.collection("quiz_intentos").where("curso_id", "==", curso_id).stream())

    feedback_positivo = 0
    feedback_negativo = 0
    feedback_pendiente = 0
    mensajes_directo = 0
    mensajes_socratico = 0
    feedback_positivo_directo = 0
    feedback_negativo_directo = 0
    feedback_positivo_socratico = 0
    feedback_negativo_socratico = 0
    for mensaje in mensajes:
        data = mensaje.to_dict() or {}
        modo = data.get("modo", "directo")
        if modo == "socratico":
            mensajes_socratico += 1
        else:
            modo = "directo"
            mensajes_directo += 1

        feedback = data.get("feedback_valor")
        if feedback == "positivo":
            feedback_positivo += 1
            if modo == "socratico":
                feedback_positivo_socratico += 1
            else:
                feedback_positivo_directo += 1
        elif feedback == "negativo":
            feedback_negativo += 1
            if modo == "socratico":
                feedback_negativo_socratico += 1
            else:
                feedback_negativo_directo += 1
        else:
            feedback_pendiente += 1

    suma_pct = 0.0
    intentos_validos = 0
    for intento in intentos:
        idata = intento.to_dict() or {}
        total = idata.get("total_preguntas") or 0
        correctas = idata.get("correctas") or 0
        if total > 0:
            suma_pct += correctas / total
            intentos_validos += 1
    promedio = round(suma_pct / intentos_validos, 3) if intentos_validos else 0.0

    return CursoAnalyticsResponse(
        curso_id=curso_id,
        total_mensajes=len(mensajes),
        total_conversaciones=len(conversaciones),
        total_documentos=len(documentos),
        total_chunks=len(chunks),
        estudiantes_matriculados=len(matriculas),
        feedback_positivo=feedback_positivo,
        feedback_negativo=feedback_negativo,
        feedback_pendiente=feedback_pendiente,
        total_quizzes=len(quizzes),
        total_intentos_quiz=len(intentos),
        promedio_aciertos_quiz=promedio,
        mensajes_directo=mensajes_directo,
        mensajes_socratico=mensajes_socratico,
        feedback_positivo_directo=feedback_positivo_directo,
        feedback_negativo_directo=feedback_negativo_directo,
        feedback_positivo_socratico=feedback_positivo_socratico,
        feedback_negativo_socratico=feedback_negativo_socratico,
        rag_backend=settings.rag_backend,
    )
