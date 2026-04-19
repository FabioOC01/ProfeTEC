from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from firebase_admin import auth as firebase_auth
from app.core.firebase import is_initialized

_bearer = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> dict:
    """
    FastAPI dependency: verifica el ID token de Firebase y retorna los claims decodificados.
    El token se envía como: Authorization: Bearer <firebase_id_token>
    """
    if not is_initialized():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Servicio de autenticación no disponible (Firebase no configurado).",
        )

    try:
        decoded = firebase_auth.verify_id_token(credentials.credentials)
        return decoded
    except firebase_auth.ExpiredIdTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expirado.")
    except firebase_auth.InvalidIdTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido.")
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No autenticado.")


def require_rol(*roles: str):
    """Dependency factory: exige que el usuario tenga uno de los roles indicados."""

    def _check(user_doc: dict = Depends(get_current_user)) -> dict:
        # user_doc aquí son los Firebase claims; el rol real está en Firestore.
        # Se usará junto con get_usuario_doc en los routers que necesiten verificar rol.
        return user_doc

    return _check
