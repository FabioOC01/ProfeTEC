import os
import firebase_admin
from firebase_admin import credentials

_initialized = False


def init_firebase() -> bool:
    """Inicializa Firebase Admin SDK. Retorna True si tuvo éxito."""
    global _initialized
    if _initialized or len(firebase_admin._apps) > 0:
        _initialized = True
        return True

    # Importar settings aquí para evitar circular imports
    from app.config import settings

    cred_path = settings.google_application_credentials or os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    project_id = settings.firebase_project_id or os.environ.get("FIREBASE_PROJECT_ID")

    try:
        if cred_path and os.path.exists(cred_path):
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
            print(f"[firebase] ✓ Inicializado con service account: {cred_path}")
        elif project_id:
            firebase_admin.initialize_app(options={"projectId": project_id})
            print(f"[firebase] ✓ Inicializado con Application Default Credentials (proyecto: {project_id})")
        else:
            print("[firebase] ⚠ Sin credenciales — endpoints de auth no disponibles.")
            return False

        _initialized = True
        return True
    except Exception as exc:
        print(f"[firebase] ✗ Error al inicializar: {exc}")
        return False


def is_initialized() -> bool:
    return _initialized or len(firebase_admin._apps) > 0
