import random
import string
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from firebase_admin import firestore

from app.core.auth import get_current_user
from app.core.firestore_client import get_db
from app.models.curso import CursoCreate, CursoResponse, CursoUpdate

router = APIRouter(prefix="/cursos", tags=["cursos"])


def _codigo_unico(length: int = 6) -> str:
    chars = string.ascii_uppercase + string.digits
    return "".join(random.choices(chars, k=length))


def _get_usuario_o_403(uid: str, db) -> dict:
    doc = db.collection("usuarios").document(uid).get()
    if not doc.exists:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Usuario no registrado.")
    return doc.to_dict()


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
    usuario = _get_usuario_o_403(uid, db)

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
    Estudiantes: ven todos los cursos activos (acceso simplificado — sin matrícula por ahora).
    """
    uid = claims["uid"]
    usuario = _get_usuario_o_403(uid, db)
    rol = usuario.get("rol")

    if rol == "docente":
        query = db.collection("cursos").where("docente_id", "==", uid)
        if activo is not None:
            query = query.where("activo", "==", activo)
    else:
        # Estudiantes ven todos los cursos activos
        query = db.collection("cursos").where("activo", "==", True)

    docs = query.stream()
    return [_doc_to_curso(d) for d in docs]


@router.get("/{curso_id}", response_model=CursoResponse, summary="Detalle de un curso (RF-05)")
def obtener_curso(
    curso_id: str,
    claims: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Cualquier usuario registrado puede ver el detalle de un curso."""
    uid = claims["uid"]
    _get_usuario_o_403(uid, db)

    doc = db.collection("cursos").document(curso_id).get()
    if not doc.exists:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Curso no encontrado.")

    return _doc_to_curso(doc)


@router.patch("/{curso_id}", response_model=CursoResponse, summary="Editar curso (RF-05)")
def editar_curso(
    curso_id: str,
    body: CursoUpdate,
    claims: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    uid = claims["uid"]
    _get_usuario_o_403(uid, db)

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
    _get_usuario_o_403(uid, db)

    ref = db.collection("cursos").document(curso_id)
    doc = ref.get()
    if not doc.exists:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Curso no encontrado.")

    if doc.to_dict()["docente_id"] != uid:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Solo el docente dueño puede eliminar este curso.")

    ref.delete()
