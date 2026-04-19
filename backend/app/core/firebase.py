import os
import firebase_admin
from firebase_admin import credentials

_initialized = False


def init_firebase() -> bool:
    """Inicializa Firebase Admin SDK. Retorna True si tuvo éxito, False en modo sin credenciales."""
    global _initialized
    if _initialized or len(firebase_admin._apps) > 0:
        _initialized = True
        return True

    cred_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    project_id = os.environ.get("FIREBASE_PROJECT_ID")

    try:
        if cred_path and os.path.exists(cred_path):
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
        elif project_id:
            # Application Default Credentials (funciona en Cloud Run automáticamente)
            firebase_admin.initialize_app(options={"projectId": project_id})
        else:
            # Sin credenciales: modo de prueba / desarrollo sin Firebase
            return False

        _initialized = True
        return True
    except Exception as exc:
        print(f"[firebase] No se pudo inicializar Firebase Admin SDK: {exc}")
        return False


def is_initialized() -> bool:
    return _initialized or len(firebase_admin._apps) > 0
