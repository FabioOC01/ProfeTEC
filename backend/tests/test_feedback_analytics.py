"""Tests de feedback de respuestas y analitica docente."""
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from app.core.auth import get_current_user
from app.core.firestore_client import get_db
from app.main import app


def _override(db, uid):
    app.dependency_overrides[get_current_user] = lambda: {"uid": uid}
    app.dependency_overrides[get_db] = lambda: db


def _clear():
    app.dependency_overrides.clear()


def test_registrar_feedback_mensaje_propio():
    db = MagicMock()
    curso_doc = MagicMock()
    curso_doc.exists = True
    curso_doc.to_dict.return_value = {"docente_id": "docente_uid", "activo": True}
    user_doc = MagicMock()
    user_doc.exists = True
    user_doc.to_dict.return_value = {"rol": "estudiante", "nombre": "Estudiante"}
    matricula_doc = MagicMock()
    matricula_doc.exists = True
    msg_doc = MagicMock()
    msg_doc.exists = True
    msg_doc.to_dict.return_value = {"curso_id": "curso1", "usuario_id": "estudiante_uid"}
    msg_ref = MagicMock()
    msg_ref.get.return_value = msg_doc

    def _collection(name):
        col = MagicMock()
        doc_ref = MagicMock()
        if name == "cursos":
            doc_ref.get.return_value = curso_doc
            col.document.return_value = doc_ref
        elif name == "usuarios":
            doc_ref.get.return_value = user_doc
            col.document.return_value = doc_ref
        elif name == "matriculas":
            doc_ref.get.return_value = matricula_doc
            col.document.return_value = doc_ref
        elif name == "mensajes":
            col.document.return_value = msg_ref
        return col

    db.collection.side_effect = _collection
    _override(db, "estudiante_uid")
    with TestClient(app) as client:
        resp = client.patch(
            "/cursos/curso1/chat/mensajes/msg1/feedback",
            json={"valor": "positivo", "comentario": "claro"},
        )
    _clear()

    assert resp.status_code == 200
    assert resp.json()["feedback_valor"] == "positivo"
    msg_ref.update.assert_called_once()


def test_analytics_docente_retorna_metricas():
    db = MagicMock()
    curso_doc = MagicMock()
    curso_doc.exists = True
    curso_doc.to_dict.return_value = {"docente_id": "docente_uid", "activo": True}
    user_doc = MagicMock()
    user_doc.exists = True
    user_doc.to_dict.return_value = {"rol": "docente", "nombre": "Prof"}

    msg_ok = MagicMock()
    msg_ok.to_dict.return_value = {"feedback_valor": "positivo", "modo": "directo"}
    msg_bad = MagicMock()
    msg_bad.to_dict.return_value = {"feedback_valor": "negativo", "modo": "socratico"}
    msg_empty = MagicMock()
    msg_empty.to_dict.return_value = {}

    def _stream_items(count):
        return [MagicMock() for _ in range(count)]

    def _collection(name):
        col = MagicMock()
        doc_ref = MagicMock()
        if name == "cursos":
            doc_ref.get.return_value = curso_doc
            col.document.return_value = doc_ref
        elif name == "usuarios":
            doc_ref.get.return_value = user_doc
            col.document.return_value = doc_ref
        elif name == "mensajes":
            col.where.return_value.stream.return_value = [msg_ok, msg_bad, msg_empty]
        elif name == "conversaciones":
            col.where.return_value.stream.return_value = _stream_items(2)
        elif name == "documentos":
            col.where.return_value.stream.return_value = _stream_items(1)
        elif name == "chunks":
            col.where.return_value.stream.return_value = _stream_items(5)
        elif name == "matriculas":
            col.where.return_value.stream.return_value = _stream_items(4)
        return col

    db.collection.side_effect = _collection
    _override(db, "docente_uid")
    with TestClient(app) as client:
        resp = client.get("/cursos/curso1/analytics")
    _clear()

    assert resp.status_code == 200
    data = resp.json()
    assert data["total_mensajes"] == 3
    assert data["total_conversaciones"] == 2
    assert data["total_documentos"] == 1
    assert data["total_chunks"] == 5
    assert data["estudiantes_matriculados"] == 4
    assert data["feedback_positivo"] == 1
    assert data["feedback_negativo"] == 1
    assert data["feedback_pendiente"] == 1
    assert data["mensajes_directo"] == 2
    assert data["mensajes_socratico"] == 1
    assert data["feedback_positivo_directo"] == 1
    assert data["feedback_negativo_socratico"] == 1
    assert data["rag_backend"] in {"firestore_scan", "bigquery_vector"}
