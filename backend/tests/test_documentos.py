"""Tests del router de documentos: upload, cleanup y permisos."""
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.core.auth import get_current_user
from app.core.firestore_client import get_db
from app.main import app
from tests.conftest import DOCENTE_CLAIMS


CURSO_ID = "curso-test"
DOC_ID = "doc-test"


def _doc(doc_id: str, data: dict, exists: bool = True):
    item = MagicMock()
    item.id = doc_id
    item.exists = exists
    item.to_dict.return_value = data
    item.reference = MagicMock()
    return item


def _db_documentos(batch_commit_side_effect=None, documento_data=None):
    db = MagicMock()
    usuario_doc = _doc(DOCENTE_CLAIMS["uid"], {"rol": "docente", "nombre": "Docente"})
    curso_doc = _doc(CURSO_ID, {"docente_id": DOCENTE_CLAIMS["uid"], "activo": True})
    documento_doc = _doc(
        DOC_ID,
        documento_data or {
            "curso_id": CURSO_ID,
            "docente_id": DOCENTE_CLAIMS["uid"],
            "storage_path": "gs://bucket/cursos/curso-test/apunte.pdf",
        },
    )
    doc_ref = MagicMock()
    doc_ref.id = DOC_ID
    doc_ref.get.return_value = documento_doc

    batch = MagicMock()
    if batch_commit_side_effect is not None:
        batch.commit.side_effect = batch_commit_side_effect
    db.batch.return_value = batch

    def _collection(name):
        col = MagicMock()
        ref = MagicMock()
        if name == "usuarios":
            ref.get.return_value = usuario_doc
            col.document.return_value = ref
        elif name == "cursos":
            ref.get.return_value = curso_doc
            col.document.return_value = ref
        elif name == "documentos":
            col.add.return_value = (None, doc_ref)
            col.document.return_value = doc_ref
            col.where.return_value.stream.return_value = [documento_doc]
        elif name == "chunks":
            chunk_ref = MagicMock()
            col.document.return_value = chunk_ref
            col.where.return_value.stream.return_value = []
        return col

    db.collection.side_effect = _collection
    return db, batch, doc_ref


def _override_db(db):
    app.dependency_overrides[get_current_user] = lambda: DOCENTE_CLAIMS
    app.dependency_overrides[get_db] = lambda: db


def _clear_overrides():
    app.dependency_overrides.clear()


@patch("app.routers.documentos.embed_texts", return_value=[[0.1, 0.2]])
@patch("app.routers.documentos.chunk_pages", return_value=[{"texto": "contenido", "pagina": 1, "posicion": 0}])
@patch("app.routers.documentos.extract_pages", return_value=[(1, "contenido")])
@patch("app.core.bigquery_rag.insert_chunk_rows")
@patch("app.routers.documentos.upload_file")
def test_subir_documento_usa_nombre_seguro_y_ruta_unica(
    mock_upload,
    mock_bq_insert,
    mock_extract,
    mock_chunk,
    mock_embed,
):
    db, batch, _doc_ref = _db_documentos()
    mock_upload.return_value = "gs://bucket/cursos/curso-test/abc_apunte.pdf"
    _override_db(db)

    with TestClient(app) as client:
        response = client.post(
            f"/cursos/{CURSO_ID}/documentos",
            data={"titulo": "Apunte semana 3", "semana": "3", "referencia": "Lectura base"},
            files={"archivo": ("../apunte.pdf", b"fake pdf", "application/pdf")},
        )
    _clear_overrides()

    assert response.status_code == 201
    assert response.json()["nombre"] == "Apunte semana 3"
    assert response.json()["semana"] == 3
    assert response.json()["referencia"] == "Lectura base"
    destination = mock_upload.call_args.kwargs["destination"]
    assert destination.startswith(f"cursos/{CURSO_ID}/")
    assert destination.endswith("_apunte.pdf")
    batch.commit.assert_called_once()
    chunk_data = batch.set.call_args.args[1]
    assert chunk_data["semana"] == 3
    assert chunk_data["referencia"] == "Lectura base"
    rows = mock_bq_insert.call_args.args[0]
    assert rows[0]["semana"] == 3
    assert rows[0]["referencia"] == "Lectura base"
    mock_bq_insert.assert_called_once()


@patch("app.routers.documentos.upload_file")
def test_subir_documento_rechaza_extension_incorrecta(mock_upload):
    db, _batch, _doc_ref = _db_documentos()
    _override_db(db)

    with TestClient(app) as client:
        response = client.post(
            f"/cursos/{CURSO_ID}/documentos",
            data={"titulo": "Apunte", "semana": "1"},
            files={"archivo": ("apunte.txt", b"fake pdf", "application/pdf")},
        )
    _clear_overrides()

    assert response.status_code == 422
    mock_upload.assert_not_called()


@patch("app.routers.documentos.embed_texts", return_value=[[0.1, 0.2]])
@patch("app.routers.documentos.chunk_pages", return_value=[{"texto": "contenido", "pagina": 1, "posicion": 0}])
@patch("app.routers.documentos.extract_pages", return_value=[(1, "contenido")])
@patch("app.routers.documentos.delete_file")
@patch("app.routers.documentos.upload_file", return_value="gs://bucket/cursos/curso-test/abc_apunte.pdf")
def test_subir_documento_limpia_storage_si_falla_firestore(
    mock_upload,
    mock_delete,
    mock_extract,
    mock_chunk,
    mock_embed,
):
    db, _batch, doc_ref = _db_documentos(batch_commit_side_effect=RuntimeError("firestore down"))
    _override_db(db)

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            f"/cursos/{CURSO_ID}/documentos",
            data={"titulo": "Apunte", "semana": "1"},
            files={"archivo": ("apunte.pdf", b"fake pdf", "application/pdf")},
        )
    _clear_overrides()

    assert response.status_code == 500
    mock_delete.assert_called_with("gs://bucket/cursos/curso-test/abc_apunte.pdf")
    doc_ref.delete.assert_called_once()


@patch("app.routers.documentos.delete_file")
@patch("app.core.bigquery_rag.delete_chunks_for_document")
def test_eliminar_documento_rechaza_si_no_pertenece_al_curso(mock_bq_delete, mock_delete):
    db, _batch, _doc_ref = _db_documentos(documento_data={
        "curso_id": "otro-curso",
        "docente_id": DOCENTE_CLAIMS["uid"],
        "storage_path": "gs://bucket/otro.pdf",
    })
    _override_db(db)

    with TestClient(app) as client:
        response = client.delete(f"/cursos/{CURSO_ID}/documentos/{DOC_ID}")
    _clear_overrides()

    assert response.status_code == 404
    mock_delete.assert_not_called()
    mock_bq_delete.assert_not_called()


@patch("app.routers.documentos.delete_file")
@patch("app.core.bigquery_rag.delete_chunks_for_document")
def test_eliminar_documento_borra_chunks_bigquery(mock_bq_delete, mock_delete):
    db, _batch, _doc_ref = _db_documentos()
    _override_db(db)

    with TestClient(app) as client:
        response = client.delete(f"/cursos/{CURSO_ID}/documentos/{DOC_ID}")
    _clear_overrides()

    assert response.status_code == 204
    mock_bq_delete.assert_called_once_with(DOC_ID)
