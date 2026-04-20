"""
Chat con el tutor RAG — endpoints de conversación (RF-13..RF-18).
Flujo: pregunta → embedding → top-k chunks → Gemini → respuesta con citas.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from firebase_admin import firestore

from app.core.auth import get_current_user
from app.core.firestore_client import get_db
from app.core.gemini import generar_respuesta
from app.core.rag import recuperar_chunks
from app.models.mensaje import ChatRequest, ChatResponse, ChunkCitado, MensajeOut

router = APIRouter(tags=["chat"])


def _verificar_acceso_curso(curso_id: str, uid: str, db) -> dict:
    """
    Cualquier usuario registrado puede chatear en cualquier curso.
    Los docentes solo chatean en sus propios cursos.
    """
    curso_doc = db.collection("cursos").document(curso_id).get()
    if not curso_doc.exists:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Curso no encontrado.")

    usuario_doc = db.collection("usuarios").document(uid).get()
    if not usuario_doc.exists:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Usuario no registrado.")

    curso_data = curso_doc.to_dict()
    usuario_data = usuario_doc.to_dict()

    # Docentes solo acceden a sus propios cursos
    if usuario_data.get("rol") == "docente" and curso_data.get("docente_id") != uid:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Los docentes solo pueden chatear en sus propios cursos.")

    return curso_data


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
    _verificar_acceso_curso(curso_id, uid, db)

    # ── 1. RAG: recuperar chunks relevantes ──────────────────────────────────
    chunks = recuperar_chunks(curso_id, body.pregunta, db)

    # ── 2. Generar respuesta con Gemini ───────────────────────────────────────
    respuesta = generar_respuesta(body.pregunta, chunks)

    # ── 3. Obtener o crear conversación ───────────────────────────────────────
    ahora = datetime.now(timezone.utc)
    conv_id = body.conversacion_id

    if conv_id:
        conv_ref = db.collection("conversaciones").document(conv_id)
        if not conv_ref.get().exists:
            conv_id = None  # no existe, crear nueva

    if not conv_id:
        _, conv_ref = db.collection("conversaciones").add({
            "curso_id": curso_id,
            "usuario_id": uid,
            "creado_en": firestore.SERVER_TIMESTAMP,
            "actualizado_en": firestore.SERVER_TIMESTAMP,
        })
        conv_id = conv_ref.id
    else:
        conv_ref.update({"actualizado_en": firestore.SERVER_TIMESTAMP})

    # ── 4. Guardar mensaje ────────────────────────────────────────────────────
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
        "chunks_usados": chunks_citados,
        "creado_en": firestore.SERVER_TIMESTAMP,
    })

    return ChatResponse(
        respuesta=respuesta,
        conversacion_id=conv_id,
        mensaje_id=msg_ref.id,
        chunks_usados=[ChunkCitado(**c) for c in chunks_citados],
        creado_en=ahora,
    )


@router.get(
    "/cursos/{curso_id}/chat/historial",
    response_model=list[MensajeOut],
    summary="Historial de mensajes del usuario en el curso (RF-18)",
)
def historial_chat(
    curso_id: str,
    claims: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Retorna los mensajes del usuario en el curso, ordenados cronológicamente."""
    uid = claims["uid"]
    _verificar_acceso_curso(curso_id, uid, db)

    mensajes_stream = (
        db.collection("mensajes")
        .where("curso_id", "==", curso_id)
        .where("usuario_id", "==", uid)
        .stream()
    )

    result = []
    for m in mensajes_stream:
        data = m.to_dict()
        created = data.get("creado_en")
        if hasattr(created, "timestamp"):
            created = datetime.fromtimestamp(created.timestamp(), tz=timezone.utc)
        else:
            created = datetime.now(timezone.utc)

        result.append(MensajeOut(
            id=m.id,
            pregunta=data.get("pregunta", ""),
            respuesta=data.get("respuesta", ""),
            chunks_usados=[ChunkCitado(**c) for c in data.get("chunks_usados", [])],
            creado_en=created,
        ))

    return sorted(result, key=lambda x: x.creado_en)
