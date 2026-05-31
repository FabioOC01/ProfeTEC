from fastapi import APIRouter, Depends, HTTPException, status
from firebase_admin import firestore

from app.config import settings
from app.core.access import docente_autorizado, validate_institutional_email
from app.core.auth import get_current_user
from app.core.firestore_client import get_db
from app.models.usuario import SetRolRequest

router = APIRouter(prefix="/auth", tags=["auth"])


def _doc_to_usuario(doc) -> dict:
    data = doc.to_dict() or {}
    data["uid"] = doc.id
    # Firestore SERVER_TIMESTAMP puede ser None en la primera escritura antes del commit
    data.pop("created_at", None)
    return data


@router.post("/me", response_model=dict, summary="Registrar o recuperar perfil del usuario")
def me(
    claims: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """
    Llamado por el frontend tras cada login de Firebase.
    - Si es el primer ingreso: crea el documento en la colección `usuarios`.
    - Si ya existe: retorna el perfil almacenado.
    Retorna `needs_onboarding: true` cuando el rol aún no está asignado (RF-02).
    """
    uid: str = claims["uid"]
    email = validate_institutional_email(
        claims.get("email"),
        settings.allowed_email_domains_list,
    )
    ref = db.collection("usuarios").document(uid)
    doc = ref.get()

    if doc.exists:
        usuario = _doc_to_usuario(doc)
        return {"usuario": usuario, "needs_onboarding": usuario.get("rol") is None}

    nuevo = {
        "email": email,
        "nombre": claims.get("name") or claims.get("email", "").split("@")[0],
        "foto_url": claims.get("picture"),
        "rol": None,
        "created_at": firestore.SERVER_TIMESTAMP,
    }
    ref.set(nuevo)
    nuevo["uid"] = uid
    nuevo.pop("created_at", None)
    return {"usuario": nuevo, "needs_onboarding": True}


@router.patch(
    "/me/rol",
    response_model=dict,
    summary="Asignar rol al usuario (onboarding — RF-02)",
)
def set_rol(
    body: SetRolRequest,
    claims: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """
    Permite al usuario elegir su rol (`docente` o `estudiante`) en el onboarding.
    Solo puede hacerse una vez; una vez asignado el rol no se puede cambiar desde aquí.
    """
    uid: str = claims["uid"]
    ref = db.collection("usuarios").document(uid)
    doc = ref.get()

    if not doc.exists:
        email = validate_institutional_email(
            claims.get("email"),
            settings.allowed_email_domains_list,
        )
        data = {
            "email": email,
            "nombre": claims.get("name") or email.split("@")[0],
            "foto_url": claims.get("picture"),
            "rol": None,
            "created_at": firestore.SERVER_TIMESTAMP,
        }
        crear_usuario = True
    else:
        data = doc.to_dict()
        crear_usuario = False

    if data.get("rol") is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El rol ya fue asignado y no se puede modificar desde este endpoint.",
        )

    email = data.get("email") or claims.get("email")
    if body.rol == "docente" and not docente_autorizado(email, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tu correo no esta autorizado para registrarse como docente.",
        )

    if crear_usuario:
        ref.set({**data, "rol": body.rol})
    else:
        ref.update({"rol": body.rol})

    data["rol"] = body.rol
    data["uid"] = uid
    data.pop("created_at", None)
    return {"usuario": data, "needs_onboarding": False}
