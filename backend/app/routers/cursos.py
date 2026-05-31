import random
import string
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from firebase_admin import firestore

from app.core.access import (
    get_usuario_o_403,
    matricula_id,
    verificar_acceso_curso,
)
from app.core.auth import get_current_user
from app.core.firestore_client import get_db
from app.models.curso import CursoCreate, CursoInscripcionRequest, CursoResponse, CursoUpdate

router = APIRouter(prefix="/cursos", tags=["cursos"])


def _codigo_unico(length: int = 6) -> str:
    chars = string.ascii_uppercase + string.digits
    return "".join(random.choices(chars, k=length))


def _doc_to_curso(doc) -> dict:
    data = doc.to_dict() or {}
    data["id"] = doc.id
    data.pop("created_at", None)
    return data


@router.post("", response_model=CursoResponse, status_code=status.HTTP_201_CREATED,
             summary="Crear curso (solo docente — RF-05)")
def crear_curso(
    body: CursoCreate,
    claims: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    uid = claims["uid"]
    usuario = get_usuario_o_403(uid, db)

    if usuario.get("rol") != "docente":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Solo los docentes pueden crear cursos.")

    nuevo = {
        "nombre": body.nombre,
        "descripcion": body.descripcion,
        "docente_id": uid,
        "docente_nombre": usuario.get("nombre", ""),
        "codigo": _codigo_unico(),
        "activo": True,
        "created_at": firestore.SERVER_TIMESTAMP,
    }
    _ref = db.collection("cursos").add(nuevo)
    doc_id = _ref[1].id
    nuevo["id"] = doc_id
    nuevo.pop("created_at", None)
    return nuevo


@router.get("", response_model=list[CursoResponse], summary="Listar cursos (RF-05)")
def listar_cursos(
    activo: Optional[bool] = None,
    claims: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """
    Docentes: ven solo sus propios cursos.
    Estudiantes: ven solo los cursos donde tienen matricula.
    """
    uid = claims["uid"]
    usuario = get_usuario_o_403(uid, db)
    rol = usuario.get("rol")

    if rol == "docente":
        query = db.collection("cursos").where("docente_id", "==", uid)
        if activo is not None:
            query = query.where("activo", "==", activo)
    elif rol == "estudiante":
        matriculas = (
            db.collection("matriculas")
            .where("usuario_id", "==", uid)
            .stream()
        )
        cursos = []
        for matricula in matriculas:
            curso_id = (matricula.to_dict() or {}).get("curso_id")
            if not curso_id:
                continue
            curso_doc = db.collection("cursos").document(curso_id).get()
            if curso_doc.exists:
                curso_data = _doc_to_curso(curso_doc)
                if curso_data.get("activo", True):
                    cursos.append(curso_data)
        return cursos
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Debes completar el onboarding antes de ver cursos.",
        )

    docs = query.stream()
    return [_doc_to_curso(d) for d in docs]


@router.post("/inscribir", response_model=CursoResponse, summary="Matricular estudiante por codigo")
def inscribir_curso(
    body: CursoInscripcionRequest,
    claims: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    uid = claims["uid"]
    usuario = get_usuario_o_403(uid, db)
    if usuario.get("rol") != "estudiante":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los estudiantes pueden matricularse por codigo.",
        )

    cursos = (
        db.collection("cursos")
        .where("codigo", "==", body.codigo)
        .where("activo", "==", True)
        .stream()
    )
    curso_doc = next(iter(cursos), None)
    if curso_doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Codigo de curso no encontrado.")

    curso = _doc_to_curso(curso_doc)
    db.collection("matriculas").document(matricula_id(curso["id"], uid)).set({
        "curso_id": curso["id"],
        "usuario_id": uid,
        "rol": "estudiante",
        "created_at": firestore.SERVER_TIMESTAMP,
    })
    return curso


@router.get("/{curso_id}", response_model=CursoResponse, summary="Detalle de un curso (RF-05)")
def obtener_curso(
    curso_id: str,
    claims: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Solo el docente dueno o estudiantes matriculados pueden ver el detalle."""
    uid = claims["uid"]
    curso, _usuario = verificar_acceso_curso(curso_id, uid, db)
    return curso


@router.patch("/{curso_id}", response_model=CursoResponse, summary="Editar curso (RF-05)")
def editar_curso(
    curso_id: str,
    body: CursoUpdate,
    claims: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    uid = claims["uid"]
    get_usuario_o_403(uid, db)

    ref = db.collection("cursos").document(curso_id)
    doc = ref.get()
    if not doc.exists:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Curso no encontrado.")

    data = doc.to_dict()
    if data["docente_id"] != uid:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Solo el docente dueño puede editar este curso.")

    cambios = body.model_dump(exclude_none=True)
    if cambios:
        ref.update(cambios)

    updated = ref.get()
    return _doc_to_curso(updated)


@router.delete("/{curso_id}", status_code=status.HTTP_204_NO_CONTENT,
               summary="Eliminar curso (RF-05)")
def eliminar_curso(
    curso_id: str,
    claims: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    uid = claims["uid"]
    get_usuario_o_403(uid, db)

    ref = db.collection("cursos").document(curso_id)
    doc = ref.get()
    if not doc.exists:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Curso no encontrado.")

    if doc.to_dict()["docente_id"] != uid:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Solo el docente dueño puede eliminar este curso.")

    ref.delete()
