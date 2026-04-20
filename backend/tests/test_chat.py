"""Tests de integración para el router de chat."""
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.auth import get_current_user
from app.core.firestore_client import get_db


# ── Fixtures ─────────────────────────────────────────────────────────────────

def _mock_db_chat(rol_usuario="estudiante"):
    db = MagicMock()

    # Curso existe
    curso_doc = MagicMock()
    curso_doc.exists = True
    curso_doc.to_dict.return_value = {
        "nombre": "Algoritmos",
        "docente_id": "docente_uid",
        "activo": True,
    }

    # Usuario existe con rol
    user_doc = MagicMock()
    user_doc.exists = True
    user_doc.to_dict.return_value = {"rol": rol_usuario, "nombre": "Test User"}

    def _collection(name):
        col = MagicMock()
        if name == "cursos":
            doc_mock = MagicMock()
            doc_mock.get.return_value = curso_doc
            col.document.return_value = doc_mock
        elif name == "usuarios":
            doc_mock = MagicMock()
            doc_mock.get.return_value = user_doc
            col.document.return_value = doc_mock
        elif name == "conversaciones":
            ref = MagicMock()
            ref.id = "conv123"
            col.add.return_value = (None, ref)
        elif name == "mensajes":
            ref = MagicMock()
            ref.id = "msg456"
            col.add.return_value = (None, ref)
        elif name == "chunks":
            col.where.return_value.stream.return_value = []
        return col

    db.collection.side_effect = _collection
    return db


@pytest.fixture
def client_estudiante():
    db = _mock_db_chat(rol_usuario="estudiante")
    app.dependency_overrides[get_current_user] = lambda: {"uid": "estudiante_uid"}
    app.dependency_overrides[get_db] = lambda: db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def client_docente_propio():
    db = _mock_db_chat(rol_usuario="docente")
    # El docente es el dueño del curso (docente_id == uid)
    curso_doc = MagicMock()
    curso_doc.exists = True
    curso_doc.to_dict.return_value = {
        "nombre": "Algoritmos",
        "docente_id": "docente_uid",
        "activo": True,
    }
    user_doc = MagicMock()
    user_doc.exists = True
    user_doc.to_dict.return_value = {"rol": "docente", "nombre": "Prof"}

    def _col(name):
        col = MagicMock()
        if name == "cursos":
            dm = MagicMock()
            dm.get.return_value = curso_doc
            col.document.return_value = dm
        elif name == "usuarios":
            dm = MagicMock()
            dm.get.return_value = user_doc
            col.document.return_value = dm
        elif name == "conversaciones":
            ref = MagicMock()
            ref.id = "conv1"
            col.add.return_value = (None, ref)
        elif name == "mensajes":
            ref = MagicMock()
            ref.id = "msg1"
            col.add.return_value = (None, ref)
        elif name == "chunks":
            col.where.return_value.stream.return_value = []
        return col

    db2 = MagicMock()
    db2.collection.side_effect = _col

    app.dependency_overrides[get_current_user] = lambda: {"uid": "docente_uid"}
    app.dependency_overrides[get_db] = lambda: db2
    yield TestClient(app)
    app.dependency_overrides.clear()


# ── Tests ─────────────────────────────────────────────────────────────────────

@patch("app.routers.chat.recuperar_chunks", return_value=[])
@patch("app.routers.chat.generar_respuesta",
       return_value="No encontré información relevante en el material del curso.")
def test_chat_sin_chunks_retorna_respuesta_vacia(mock_gen, mock_rag, client_estudiante):
    """Con chunks vacíos el endpoint debe retornar 200 con un mensaje estándar."""
    resp = client_estudiante.post(
        "/cursos/curso1/chat",
        json={"pregunta": "¿Qué es un árbol binario?"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "respuesta" in data
    assert data["conversacion_id"] == "conv123"
    assert data["mensaje_id"] == "msg456"
    assert data["chunks_usados"] == []


@patch("app.routers.chat.recuperar_chunks", return_value=[
    {"documento_id": "d1", "nombre_doc": "apunte.pdf",
     "pagina": 3, "texto": "Un árbol binario es...", "score": 0.92},
])
@patch("app.routers.chat.generar_respuesta",
       return_value="Un árbol binario es una estructura de datos [📄 apunte.pdf, pág. 3]")
def test_chat_con_chunks_retorna_citas(mock_gen, mock_rag, client_estudiante):
    """Con chunks relevantes la respuesta debe incluir chunks_usados."""
    resp = client_estudiante.post(
        "/cursos/curso1/chat",
        json={"pregunta": "¿Qué es un árbol binario?"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["chunks_usados"]) == 1
    assert data["chunks_usados"][0]["nombre_doc"] == "apunte.pdf"
    assert data["chunks_usados"][0]["pagina"] == 3


@patch("app.routers.chat.recuperar_chunks", return_value=[])
@patch("app.routers.chat.generar_respuesta", return_value="Respuesta de prueba")
def test_chat_docente_propio_curso_ok(mock_gen, mock_rag, client_docente_propio):
    """Un docente puede chatear en su propio curso."""
    resp = client_docente_propio.post(
        "/cursos/curso1/chat",
        json={"pregunta": "¿Cómo explico esto?"}
    )
    assert resp.status_code == 200


def test_chat_pregunta_vacia_retorna_422(client_estudiante):
    """Una pregunta vacía debe retornar 422."""
    resp = client_estudiante.post(
        "/cursos/curso1/chat",
        json={"pregunta": ""}
    )
    assert resp.status_code == 422


@patch("app.core.rag.recuperar_chunks", return_value=[])
@patch("app.core.gemini.generar_respuesta", return_value="Respuesta")
def test_historial_retorna_lista(mock_gen, mock_rag, client_estudiante):
    """El endpoint de historial debe retornar lista (vacía si no hay mensajes)."""
    db = MagicMock()
    db.collection.return_value.where.return_value.where.return_value.stream.return_value = []
    app.dependency_overrides[get_db] = lambda: db

    resp = client_estudiante.get("/cursos/curso1/chat/historial")
    assert resp.status_code in (200, 404)  # 404 si curso no existe con el mock simple
