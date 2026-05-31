"""Endpoints de quizzes (RF-20..RF-23).

Reglas de acceso:
- Crear / eliminar quiz: solo el docente dueño del curso.
- Listar / ver quiz para responder: docente dueño y estudiantes matriculados.
- Enviar intento: solo estudiantes matriculados.
- Ver intentos: cada estudiante solo los suyos; el docente ve todos los del curso.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from firebase_admin import firestore

from app.core.access import verificar_acceso_curso
from app.core.auth import get_current_user
from app.core.firestore_client import get_db
from app.core.quiz_generator import generar_preguntas
from app.models.quiz import (
    DetallePregunta,
    IntentoCreate,
    IntentoResultado,
    IntentoResumen,
    PreguntaParaResponder,
    PreguntaQuiz,
    QuizCreate,
    QuizDetalleDocente,
    QuizParaTomar,
    QuizResumen,
)

router = APIRouter(tags=["quizzes"])


def _curso_docente_o_403(curso_id: str, uid: str, db) -> dict:
    curso, usuario = verificar_acceso_curso(curso_id, uid, db)
    if usuario.get("rol") != "docente" or curso.get("docente_id") != uid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo el docente dueño puede ejecutar esta acción.",
        )
    return curso


def _curso_estudiante_o_403(curso_id: str, uid: str, db) -> dict:
    curso, usuario = verificar_acceso_curso(curso_id, uid, db)
    if usuario.get("rol") != "estudiante":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los estudiantes pueden enviar respuestas a un quiz.",
        )
    return curso


def _quiz_del_curso_o_404(curso_id: str, quiz_id: str, db) -> dict:
    doc = db.collection("quizzes").document(quiz_id).get()
    if not doc.exists:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz no encontrado.")
    data = doc.to_dict() or {}
    if data.get("curso_id") != curso_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El quiz no pertenece a este curso.",
        )
    data["id"] = doc.id
    return data


def _to_datetime(value) -> datetime:
    if hasattr(value, "timestamp"):
        return datetime.fromtimestamp(value.timestamp(), tz=timezone.utc)
    if isinstance(value, datetime):
        return value
    return datetime.now(timezone.utc)


def _normalizar_rango_semana(body: QuizCreate) -> tuple[int | None, int | None]:
    desde = body.semana_desde
    hasta = body.semana_hasta
    if desde is None and hasta is None:
        return None, None
    if desde is None:
        desde = hasta
    if hasta is None:
        hasta = desde
    if desde is not None and hasta is not None and desde > hasta:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="semana_desde no puede ser mayor que semana_hasta.",
        )
    return desde, hasta


@router.post(
    "/cursos/{curso_id}/quizzes",
    response_model=QuizDetalleDocente,
    status_code=status.HTTP_201_CREATED,
    summary="Generar un quiz a partir del material del curso (RF-20, RF-21)",
)
def crear_quiz(
    curso_id: str,
    body: QuizCreate,
    claims: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    uid = claims["uid"]
    _curso_docente_o_403(curso_id, uid, db)
    semana_desde, semana_hasta = _normalizar_rango_semana(body)

    try:
        preguntas = generar_preguntas(
            curso_id,
            body.tema,
            body.num_preguntas,
            db,
            semana_desde=semana_desde,
            semana_hasta=semana_hasta,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    ahora = datetime.now(timezone.utc)
    _, ref = db.collection("quizzes").add({
        "curso_id": curso_id,
        "docente_id": uid,
        "titulo": body.titulo,
        "tema": body.tema,
        "semana_desde": semana_desde,
        "semana_hasta": semana_hasta,
        "preguntas": preguntas,
        "creado_en": firestore.SERVER_TIMESTAMP,
    })

    return QuizDetalleDocente(
        id=ref.id,
        curso_id=curso_id,
        titulo=body.titulo,
        tema=body.tema,
        semana_desde=semana_desde,
        semana_hasta=semana_hasta,
        preguntas=[PreguntaQuiz(**p) for p in preguntas],
        creado_en=ahora,
    )


@router.get(
    "/cursos/{curso_id}/quizzes",
    response_model=list[QuizResumen],
    summary="Listar quizzes del curso (RF-22)",
)
def listar_quizzes(
    curso_id: str,
    claims: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    uid = claims["uid"]
    verificar_acceso_curso(curso_id, uid, db)

    quizzes = db.collection("quizzes").where("curso_id", "==", curso_id).stream()
    out: list[QuizResumen] = []
    for q in quizzes:
        data = q.to_dict() or {}
        out.append(QuizResumen(
            id=q.id,
            titulo=data.get("titulo", ""),
            tema=data.get("tema"),
            num_preguntas=len(data.get("preguntas") or []),
            semana_desde=data.get("semana_desde"),
            semana_hasta=data.get("semana_hasta"),
            creado_en=_to_datetime(data.get("creado_en")),
        ))
    return sorted(out, key=lambda x: x.creado_en, reverse=True)


@router.get(
    "/cursos/{curso_id}/quizzes/{quiz_id}",
    summary="Detalle de un quiz (docente: completo; estudiante: para responder)",
)
def detalle_quiz(
    curso_id: str,
    quiz_id: str,
    claims: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    uid = claims["uid"]
    _, usuario = verificar_acceso_curso(curso_id, uid, db)
    data = _quiz_del_curso_o_404(curso_id, quiz_id, db)

    preguntas = data.get("preguntas") or []
    if usuario.get("rol") == "docente":
        return QuizDetalleDocente(
            id=data["id"],
            curso_id=curso_id,
            titulo=data.get("titulo", ""),
            tema=data.get("tema"),
            semana_desde=data.get("semana_desde"),
            semana_hasta=data.get("semana_hasta"),
            preguntas=[PreguntaQuiz(**p) for p in preguntas],
            creado_en=_to_datetime(data.get("creado_en")),
        )

    # Estudiante: ocultar indice_correcto y explicacion
    preguntas_seguras = [
        PreguntaParaResponder(
            texto=p.get("texto", ""),
            opciones=p.get("opciones") or [],
            nombre_doc=p.get("nombre_doc"),
            pagina=p.get("pagina"),
        )
        for p in preguntas
    ]
    return QuizParaTomar(
        id=data["id"],
        curso_id=curso_id,
        titulo=data.get("titulo", ""),
        tema=data.get("tema"),
        semana_desde=data.get("semana_desde"),
        semana_hasta=data.get("semana_hasta"),
        preguntas=preguntas_seguras,
    )


@router.delete(
    "/cursos/{curso_id}/quizzes/{quiz_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar un quiz (docente dueño)",
)
def eliminar_quiz(
    curso_id: str,
    quiz_id: str,
    claims: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    uid = claims["uid"]
    _curso_docente_o_403(curso_id, uid, db)
    quiz = _quiz_del_curso_o_404(curso_id, quiz_id, db)
    if quiz.get("docente_id") != uid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo el docente que creó el quiz puede eliminarlo.",
        )
    db.collection("quizzes").document(quiz_id).delete()


@router.post(
    "/cursos/{curso_id}/quizzes/{quiz_id}/intentos",
    response_model=IntentoResultado,
    status_code=status.HTTP_201_CREATED,
    summary="Estudiante envía respuestas y recibe la corrección (RF-23)",
)
def crear_intento(
    curso_id: str,
    quiz_id: str,
    body: IntentoCreate,
    claims: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    uid = claims["uid"]
    _curso_estudiante_o_403(curso_id, uid, db)
    quiz = _quiz_del_curso_o_404(curso_id, quiz_id, db)

    preguntas = quiz.get("preguntas") or []
    total = len(preguntas)
    if total == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El quiz no tiene preguntas.",
        )
    if len(body.respuestas) != total:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Debes responder exactamente {total} preguntas.",
        )

    detalle: list[dict] = []
    correctas = 0
    for i, pregunta in enumerate(preguntas):
        opciones = pregunta.get("opciones") or []
        correcta = int(pregunta.get("indice_correcto", 0))
        elegida = int(body.respuestas[i])
        if elegida < 0 or elegida >= len(opciones):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Respuesta fuera de rango en la pregunta {i + 1}.",
            )
        es_correcta = elegida == correcta
        if es_correcta:
            correctas += 1
        detalle.append({
            "indice_pregunta": i,
            "texto": pregunta.get("texto", ""),
            "opciones": opciones,
            "elegida": elegida,
            "correcta": correcta,
            "es_correcta": es_correcta,
            "explicacion": pregunta.get("explicacion"),
        })

    porcentaje = round(correctas / total, 3)
    ahora = datetime.now(timezone.utc)

    _, intento_ref = db.collection("quiz_intentos").add({
        "quiz_id": quiz_id,
        "curso_id": curso_id,
        "usuario_id": uid,
        "usuario_nombre": claims.get("name") or claims.get("email"),
        "respuestas": list(body.respuestas),
        "correctas": correctas,
        "total_preguntas": total,
        "porcentaje": porcentaje,
        "detalle": detalle,
        "completado_en": firestore.SERVER_TIMESTAMP,
    })

    return IntentoResultado(
        id=intento_ref.id,
        quiz_id=quiz_id,
        correctas=correctas,
        total_preguntas=total,
        porcentaje=porcentaje,
        detalle=[DetallePregunta(**d) for d in detalle],
        completado_en=ahora,
    )


@router.get(
    "/cursos/{curso_id}/quizzes/{quiz_id}/intentos",
    response_model=list[IntentoResumen],
    summary="Listar intentos de un quiz (docente: todos; estudiante: los suyos)",
)
def listar_intentos(
    curso_id: str,
    quiz_id: str,
    claims: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    uid = claims["uid"]
    _, usuario = verificar_acceso_curso(curso_id, uid, db)
    _quiz_del_curso_o_404(curso_id, quiz_id, db)

    query = db.collection("quiz_intentos").where("quiz_id", "==", quiz_id)
    if usuario.get("rol") == "estudiante":
        query = query.where("usuario_id", "==", uid)

    out: list[IntentoResumen] = []
    for intento in query.stream():
        data = intento.to_dict() or {}
        total = int(data.get("total_preguntas", 0)) or 1
        correctas = int(data.get("correctas", 0))
        out.append(IntentoResumen(
            id=intento.id,
            quiz_id=quiz_id,
            usuario_id=data.get("usuario_id", ""),
            usuario_nombre=data.get("usuario_nombre"),
            correctas=correctas,
            total_preguntas=total,
            porcentaje=round(correctas / total, 3),
            completado_en=_to_datetime(data.get("completado_en")),
        ))
    return sorted(out, key=lambda x: x.completado_en, reverse=True)
