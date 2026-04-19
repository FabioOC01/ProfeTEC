from firebase_admin import firestore
from app.core.firebase import is_initialized


def get_db():
    """FastAPI dependency: retorna el cliente de Firestore."""
    if not is_initialized():
        raise RuntimeError(
            "Firebase no está inicializado. "
            "Configura GOOGLE_APPLICATION_CREDENTIALS o FIREBASE_PROJECT_ID en .env"
        )
    return firestore.client()
