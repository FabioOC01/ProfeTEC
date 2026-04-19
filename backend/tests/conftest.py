"""
Fixtures compartidos para los tests del Sprint 1.
Los mocks reemplazan Firebase y Firestore para que los tests corran sin credenciales reales.
"""
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.core.auth import get_current_user
from app.core.firestore_client import get_db

# ── Claims de Firebase simulados ───────────────────────────────────────────────
DOCENTE_CLAIMS = {
    "uid": "uid-docente-test",
    "email": "docente@tecsup.edu.pe",
    "name": "Docente Prueba",
    "picture": None,
}

ESTUDIANTE_CLAIMS = {
    "uid": "uid-estudiante-test",
    "email": "estudiante@tecsup.edu.pe",
    "name": "Estudiante Prueba",
    "picture": None,
}


# ── Helpers para construir documentos Firestore falsos ─────────────────────────

def _make_doc(doc_id: str, data: dict):
    doc = MagicMock()
    doc.id = doc_id
    doc.exists = True
    doc.to_dict.return_value = data
    return doc


def _make_missing_doc():
    doc = MagicMock()
    doc.exists = False
    doc.to_dict.return_value = {}
    return doc


# ── Fixtures de cliente HTTP ────────────────────────────────────────────────────

@pytest.fixture
def db_mock():
    return MagicMock()


@pytest.fixture
def client_docente(db_mock):
    """Cliente HTTP autenticado como docente con rol asignado."""
    usuario_data = {
        "email": DOCENTE_CLAIMS["email"],
        "nombre": DOCENTE_CLAIMS["name"],
        "foto_url": None,
        "rol": "docente",
    }
    db_mock.collection.return_value.document.return_value.get.return_value = (
        _make_doc(DOCENTE_CLAIMS["uid"], usuario_data)
    )

    app.dependency_overrides[get_current_user] = lambda: DOCENTE_CLAIMS
    app.dependency_overrides[get_db] = lambda: db_mock
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def client_sin_rol(db_mock):
    """Cliente HTTP autenticado como usuario sin rol (primer ingreso)."""
    usuario_data = {
        "email": DOCENTE_CLAIMS["email"],
        "nombre": DOCENTE_CLAIMS["name"],
        "foto_url": None,
        "rol": None,
    }
    db_mock.collection.return_value.document.return_value.get.return_value = (
        _make_doc(DOCENTE_CLAIMS["uid"], usuario_data)
    )

    app.dependency_overrides[get_current_user] = lambda: DOCENTE_CLAIMS
    app.dependency_overrides[get_db] = lambda: db_mock
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def client_nuevo_usuario(db_mock):
    """Cliente HTTP: usuario autenticado pero sin documento en Firestore aún."""
    db_mock.collection.return_value.document.return_value.get.return_value = (
        _make_missing_doc()
    )
    db_mock.collection.return_value.document.return_value.set.return_value = None

    app.dependency_overrides[get_current_user] = lambda: DOCENTE_CLAIMS
    app.dependency_overrides[get_db] = lambda: db_mock
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
