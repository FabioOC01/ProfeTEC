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
            conv_doc = MagicMock()
            conv_doc.exists = True
            conv_doc.to_dict.return_value = {
                "curso_id": "curso1",
                "usuario_id": "estudiante_uid" if rol_usuario == "estudiante" else "docente_uid",
            }
            ref.get.return_value = conv_doc
            col.document.return_value = ref
            col.add.return_value = (None, ref)
        elif name == "mensajes":
            ref = MagicMock()
            ref.id = "msg456"
            col.add.return_value = (None, ref)
            col.where.return_value.where.return_value.stream.return_value = []
        elif name == "chunks":
            col.where.return_value.stream.return_value = []
        elif name == "matriculas":
            doc_mock = MagicMock()
            matricula_doc = MagicMock()
            matricula_doc.exists = True
            doc_mock.get.return_value = matricula_doc
            col.document.return_value = doc_mock
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
            conv_doc = MagicMock()
            conv_doc.exists = True
            conv_doc.to_dict.return_value = {"curso_id": "curso1", "usuario_id": "docente_uid"}
            ref.get.return_value = conv_doc
            col.document.return_value = ref
            col.add.return_value = (None, ref)
        elif name == "mensajes":
            ref = MagicMock()
            ref.id = "msg1"
            col.add.return_value = (None, ref)
            col.where.return_value.where.return_value.stream.return_value = []
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
    assert data["modo"] == "directo"
    mock_gen.assert_called_once()
    assert mock_gen.call_args.args[2] == "directo"


@patch("app.routers.chat.recuperar_chunks", return_value=[])
@patch("app.routers.chat.generar_respuesta", return_value="Probemos paso a paso.")
def test_chat_socratico_envia_y_persiste_modo(mock_gen, mock_rag):
    db = MagicMock()
    curso_doc = MagicMock()
    curso_doc.exists = True
    curso_doc.to_dict.return_value = {
        "nombre": "Algoritmos",
        "docente_id": "docente_uid",
        "activo": True,
    }
    user_doc = MagicMock()
    user_doc.exists = True
    user_doc.to_dict.return_value = {"rol": "estudiante", "nombre": "Test User"}
    matricula_doc = MagicMock()
    matricula_doc.exists = True
    conv_ref = MagicMock()
    conv_ref.id = "conv-socratico"
    msg_ref = MagicMock()
    msg_ref.id = "msg-socratico"
    mensajes_col = MagicMock()
    mensajes_col.add.return_value = (None, msg_ref)

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
        elif name == "conversaciones":
            col.add.return_value = (None, conv_ref)
        elif name == "mensajes":
            return mensajes_col
        elif name == "chunks":
            col.where.return_value.stream.return_value = []
        return col

    db.collection.side_effect = _collection
    app.dependency_overrides[get_current_user] = lambda: {"uid": "estudiante_uid"}
    app.dependency_overrides[get_db] = lambda: db

    with TestClient(app) as client:
        resp = client.post(
            "/cursos/curso1/chat",
            json={"pregunta": "No entiendo arboles", "modo": "socratico"},
        )
    app.dependency_overrides.clear()

    assert resp.status_code == 200
    assert resp.json()["modo"] == "socratico"
    mock_gen.assert_called_once()
    assert mock_gen.call_args.args[2] == "socratico"
    saved = mensajes_col.add.call_args.args[0]
    assert saved["modo"] == "socratico"


@patch("app.routers.chat.recuperar_chunks", return_value=[])
@patch("app.routers.chat.generar_respuesta", return_value="Respuesta de prueba")
def test_chat_docente_propio_curso_ok(mock_gen, mock_rag, client_docente_propio):
    """Un docente puede chatear en su propio curso."""
    resp = client_docente_propio.post(
        "/cursos/curso1/chat",
        json={"pregunta": "¿Cómo explico esto?"}
    )
    assert resp.status_code == 200


@patch("app.routers.chat.recuperar_chunks")
@patch("app.routers.chat.generar_respuesta")
def test_chat_gracias_responde_sin_rag_ni_gemini(mock_gen, mock_rag, client_estudiante):
    resp = client_estudiante.post(
        "/cursos/curso1/chat",
        json={"pregunta": "gracias", "modo": "socratico"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["chunks_usados"] == []
    assert data["respuesta"].startswith("De nada")
    mock_rag.assert_not_called()
    mock_gen.assert_not_called()


@patch("app.routers.chat.recuperar_chunks")
@patch("app.routers.chat.generar_respuesta")
def test_chat_identidad_responde_sin_rag_ni_gemini(mock_gen, mock_rag, client_estudiante):
    resp = client_estudiante.post(
        "/cursos/curso1/chat",
        json={"pregunta": "¿Quién eres?", "modo": "directo"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["chunks_usados"] == []
    assert "ProfeTEC.IA" in data["respuesta"]
    mock_rag.assert_not_called()
    mock_gen.assert_not_called()


@patch("app.routers.chat.recuperar_chunks", return_value=[])
@patch("app.routers.chat.generar_respuesta_stream", return_value=iter(["Hola ", "mundo"]))
def test_chat_stream_emite_delta_y_done(mock_stream, mock_rag, client_estudiante):
    resp = client_estudiante.post(
        "/cursos/curso1/chat/stream",
        json={"pregunta": "Explica el tema principal", "modo": "directo"},
    )

    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers["content-type"]
    body = resp.text
    assert "event: status" in body
    assert 'event: delta\ndata: {"text": "Hola "}' in body
    assert 'event: delta\ndata: {"text": "mundo"}' in body
    assert "event: done" in body
    assert '"respuesta": "Hola mundo"' in body


def test_chat_pregunta_vacia_retorna_422(client_estudiante):
    """Una pregunta vacía debe retornar 422."""
    resp = client_estudiante.post(
        "/cursos/curso1/chat",
        json={"pregunta": ""}
    )
    assert resp.status_code == 422


@patch("app.routers.chat.recuperar_chunks", return_value=[])
@patch("app.routers.chat.generar_respuesta", return_value="Respuesta")
def test_chat_rechaza_conversacion_ajena(mock_gen, mock_rag):
    """No se puede reutilizar una conversacion de otro usuario."""
    db = MagicMock()
    curso_doc = MagicMock()
    curso_doc.exists = True
    curso_doc.to_dict.return_value = {
        "nombre": "Algoritmos",
        "docente_id": "docente_uid",
        "activo": True,
    }
    user_doc = MagicMock()
    user_doc.exists = True
    user_doc.to_dict.return_value = {"rol": "estudiante", "nombre": "Test User"}
    matricula_doc = MagicMock()
    matricula_doc.exists = True
    conv_doc = MagicMock()
    conv_doc.exists = True
    conv_doc.to_dict.return_value = {"curso_id": "curso1", "usuario_id": "otro_uid"}

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
        elif name == "conversaciones":
            doc_ref.get.return_value = conv_doc
            col.document.return_value = doc_ref
        elif name == "chunks":
            col.where.return_value.stream.return_value = []
        return col

    db.collection.side_effect = _collection

    app.dependency_overrides[get_current_user] = lambda: {"uid": "estudiante_uid"}
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as client:
        resp = client.post(
            "/cursos/curso1/chat",
            json={"pregunta": "Hola", "conversacion_id": "conv-ajena"},
        )
    app.dependency_overrides.clear()

    assert resp.status_code == 403


@patch("app.core.rag.recuperar_chunks", return_value=[])
@patch("app.core.gemini.generar_respuesta", return_value="Respuesta")
def test_historial_retorna_lista(mock_gen, mock_rag, client_estudiante):
    """El endpoint de historial debe retornar lista (vacía si no hay mensajes)."""
    resp = client_estudiante.get("/cursos/curso1/chat/historial")
    assert resp.status_code == 200


def test_listar_conversaciones_ordenadas():
    """El endpoint de conversaciones devuelve los hilos del usuario, recientes primero."""
    from datetime import datetime, timezone

    db = MagicMock()
    curso_doc = MagicMock()
    curso_doc.exists = True
    curso_doc.to_dict.return_value = {
        "nombre": "Algoritmos", "docente_id": "docente_uid", "activo": True,
    }
    user_doc = MagicMock()
    user_doc.exists = True
    user_doc.to_dict.return_value = {"rol": "estudiante", "nombre": "Test User"}
    matricula_doc = MagicMock()
    matricula_doc.exists = True

    class _TS:
        def __init__(self, t):
            self._t = t

        def timestamp(self):
            return self._t

    conv_a = MagicMock()
    conv_a.id = "conv-vieja"
    conv_a.to_dict.return_value = {
        "curso_id": "curso1", "usuario_id": "estudiante_uid",
        "titulo": "Embeddings", "actualizado_en": _TS(100.0),
    }
    conv_b = MagicMock()
    conv_b.id = "conv-nueva"
    conv_b.to_dict.return_value = {
        "curso_id": "curso1", "usuario_id": "estudiante_uid",
        "titulo": "Chunking", "actualizado_en": _TS(200.0),
    }

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
        elif name == "conversaciones":
            col.where.return_value.where.return_value.stream.return_value = [conv_a, conv_b]
        return col

    db.collection.side_effect = _collection
    app.dependency_overrides[get_current_user] = lambda: {"uid": "estudiante_uid"}
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as client:
        resp = client.get("/cursos/curso1/conversaciones")
    app.dependency_overrides.clear()

    assert resp.status_code == 200
    data = resp.json()
    assert [c["id"] for c in data] == ["conv-nueva", "conv-vieja"]
    assert data[0]["titulo"] == "Chunking"


@patch("app.routers.chat.reescribir_consulta", side_effect=lambda p, h: p)
@patch("app.routers.chat.recuperar_chunks", return_value=[])
@patch("app.routers.chat.generar_respuesta", return_value="Sigue pensando.")
def test_chat_pasa_historial_a_gemini(mock_gen, mock_rag, mock_reescribir):
    """Al reusar una conversación existente, los turnos previos se pasan como memoria."""
    class _TS:
        def __init__(self, t):
            self._t = t

        def timestamp(self):
            return self._t

    db = MagicMock()
    curso_doc = MagicMock()
    curso_doc.exists = True
    curso_doc.to_dict.return_value = {
        "nombre": "Algoritmos", "docente_id": "docente_uid", "activo": True,
    }
    user_doc = MagicMock()
    user_doc.exists = True
    user_doc.to_dict.return_value = {"rol": "estudiante", "nombre": "Test User"}
    matricula_doc = MagicMock()
    matricula_doc.exists = True

    conv_ref = MagicMock()
    conv_ref.id = "conv-existente"
    conv_doc = MagicMock()
    conv_doc.exists = True
    conv_doc.to_dict.return_value = {"curso_id": "curso1", "usuario_id": "estudiante_uid"}
    conv_ref.get.return_value = conv_doc

    msg_prev = MagicMock()
    msg_prev.to_dict.return_value = {
        "pregunta": "¿Qué es un árbol?", "respuesta": "Pista: piensa en jerarquía.",
        "usuario_id": "estudiante_uid", "creado_en": _TS(10.0),
    }
    msg_ref = MagicMock()
    msg_ref.id = "msg-nuevo"
    mensajes_col = MagicMock()
    mensajes_col.where.return_value.stream.return_value = [msg_prev]
    mensajes_col.add.return_value = (None, msg_ref)

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
        elif name == "conversaciones":
            col.document.return_value = conv_ref
        elif name == "mensajes":
            return mensajes_col
        return col

    db.collection.side_effect = _collection
    app.dependency_overrides[get_current_user] = lambda: {"uid": "estudiante_uid"}
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as client:
        resp = client.post(
            "/cursos/curso1/chat",
            json={
                "pregunta": "Sigo sin entender",
                "conversacion_id": "conv-existente",
                "modo": "socratico",
            },
        )
    app.dependency_overrides.clear()

    assert resp.status_code == 200
    historial = mock_gen.call_args.args[3]
    assert historial == [
        {"pregunta": "¿Qué es un árbol?", "respuesta": "Pista: piensa en jerarquía."}
    ]
    # El seguimiento se reescribe con el historial antes de buscar en el RAG.
    mock_reescribir.assert_called_once_with("Sigo sin entender", historial)


@patch("app.routers.chat.reescribir_consulta",
       return_value="Elementos del análisis FODA además de fortalezas y debilidades")
@patch("app.routers.chat.recuperar_chunks", return_value=[])
@patch("app.routers.chat.generar_respuesta", return_value="Las otras dos son oportunidades y amenazas.")
def test_chat_busca_con_consulta_reescrita(mock_gen, mock_rag, mock_reescribir):
    """El RAG debe buscar con la consulta reescrita, no con el texto literal corto."""
    class _TS:
        def __init__(self, t):
            self._t = t

        def timestamp(self):
            return self._t

    db = MagicMock()
    curso_doc = MagicMock()
    curso_doc.exists = True
    curso_doc.to_dict.return_value = {
        "nombre": "Consultoría", "docente_id": "docente_uid", "activo": True,
    }
    user_doc = MagicMock()
    user_doc.exists = True
    user_doc.to_dict.return_value = {"rol": "estudiante", "nombre": "Test User"}
    matricula_doc = MagicMock()
    matricula_doc.exists = True

    conv_ref = MagicMock()
    conv_ref.id = "conv-foda"
    conv_doc = MagicMock()
    conv_doc.exists = True
    conv_doc.to_dict.return_value = {"curso_id": "curso1", "usuario_id": "estudiante_uid"}
    conv_ref.get.return_value = conv_doc

    msg_prev = MagicMock()
    msg_prev.to_dict.return_value = {
        "pregunta": "¿Qué significa FODA?",
        "respuesta": "¿Qué otros elementos se mencionan además de fortalezas y debilidades?",
        "usuario_id": "estudiante_uid", "creado_en": _TS(10.0),
    }
    msg_ref = MagicMock()
    msg_ref.id = "msg-nuevo"
    mensajes_col = MagicMock()
    mensajes_col.where.return_value.stream.return_value = [msg_prev]
    mensajes_col.add.return_value = (None, msg_ref)

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
        elif name == "conversaciones":
            col.document.return_value = conv_ref
        elif name == "mensajes":
            return mensajes_col
        return col

    db.collection.side_effect = _collection
    app.dependency_overrides[get_current_user] = lambda: {"uid": "estudiante_uid"}
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as client:
        resp = client.post(
            "/cursos/curso1/chat",
            json={
                "pregunta": "No lo sé, ayúdame",
                "conversacion_id": "conv-foda",
                "modo": "socratico",
            },
        )
    app.dependency_overrides.clear()

    assert resp.status_code == 200
    # recuperar_chunks recibe la consulta reescrita, no "No lo sé, ayúdame".
    consulta_usada = mock_rag.call_args.args[1]
    assert consulta_usada == "Elementos del análisis FODA además de fortalezas y debilidades"


# ── Tests de rendicion, contexto_debil y fallback de chunks ──────────────────

@patch("app.routers.chat.reescribir_consulta", side_effect=lambda p, h: p)
@patch("app.routers.chat.recuperar_chunks", return_value=[])
@patch("app.routers.chat.generar_respuesta", return_value="Las oportunidades y amenazas.")
def test_chat_rendicion_pasa_flag_a_gemini(mock_gen, mock_rag, mock_reescribir):
    """Cuando el estudiante se rinde en socrático, generar_respuesta recibe rendicion=True."""
    db = _mock_db_chat(rol_usuario="estudiante")
    app.dependency_overrides[get_current_user] = lambda: {"uid": "estudiante_uid"}
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as client:
        resp = client.post(
            "/cursos/curso1/chat",
            json={"pregunta": "no lo sé", "modo": "socratico"},
        )
    app.dependency_overrides.clear()

    assert resp.status_code == 200
    _, _, _, _, rendicion, _ = mock_gen.call_args.args
    assert rendicion is True


@patch("app.routers.chat.reescribir_consulta", side_effect=lambda p, h: p)
@patch("app.routers.chat.recuperar_chunks", return_value=[
    {"documento_id": "d1", "nombre_doc": "FODA.pdf", "pagina": 2,
     "texto": "Fortalezas...", "score": 0.45},
])
@patch("app.routers.chat.generar_respuesta", return_value="Respuesta con score bajo.")
def test_chat_contexto_debil_cuando_score_bajo(mock_gen, mock_rag, mock_reescribir):
    """Si el mejor score del RAG < rag_score_confianza, se pasa contexto_debil=True."""
    db = _mock_db_chat(rol_usuario="estudiante")
    app.dependency_overrides[get_current_user] = lambda: {"uid": "estudiante_uid"}
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as client:
        resp = client.post(
            "/cursos/curso1/chat",
            json={"pregunta": "¿Qué es FODA?"},
        )
    app.dependency_overrides.clear()

    assert resp.status_code == 200
    _, _, _, _, _, contexto_debil = mock_gen.call_args.args
    # Score 0.45 < rag_score_confianza (0.6) → contexto_debil debe ser True.
    assert contexto_debil is True


@patch("app.routers.chat.reescribir_consulta", side_effect=lambda p, h: p)
@patch("app.routers.chat.recuperar_chunks", return_value=[
    {"documento_id": "d1", "nombre_doc": "FODA.pdf", "pagina": 2,
     "texto": "Fortalezas...", "score": 0.85},
])
@patch("app.routers.chat.generar_respuesta", return_value="Respuesta con buen score.")
def test_chat_contexto_solido_cuando_score_alto(mock_gen, mock_rag, mock_reescribir):
    """Si el mejor score >= rag_score_confianza, contexto_debil=False."""
    db = _mock_db_chat(rol_usuario="estudiante")
    app.dependency_overrides[get_current_user] = lambda: {"uid": "estudiante_uid"}
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as client:
        resp = client.post(
            "/cursos/curso1/chat",
            json={"pregunta": "¿Qué es FODA?"},
        )
    app.dependency_overrides.clear()

    assert resp.status_code == 200
    _, _, _, _, _, contexto_debil = mock_gen.call_args.args
    assert contexto_debil is False


@patch("app.routers.chat.reescribir_consulta", side_effect=lambda p, h: p)
@patch("app.routers.chat.recuperar_chunks", return_value=[])
@patch("app.routers.chat.generar_respuesta", return_value="Respuesta con fallback.")
def test_chat_fallback_usa_chunks_del_turno_anterior(mock_gen, mock_rag, mock_reescribir):
    """Cuando la búsqueda trae chunks vacíos en una conversación existente,
    se reutilizan los chunks_usados del mensaje anterior."""
    class _TS:
        def __init__(self, t):
            self._t = t
        def timestamp(self):
            return self._t

    db = MagicMock()
    curso_doc = MagicMock()
    curso_doc.exists = True
    curso_doc.to_dict.return_value = {"nombre": "Curso", "docente_id": "docente_uid", "activo": True}
    user_doc = MagicMock()
    user_doc.exists = True
    user_doc.to_dict.return_value = {"rol": "estudiante", "nombre": "Test"}
    matricula_doc = MagicMock()
    matricula_doc.exists = True

    conv_ref = MagicMock()
    conv_ref.id = "conv-fallback"
    conv_doc = MagicMock()
    conv_doc.exists = True
    conv_doc.to_dict.return_value = {"curso_id": "curso1", "usuario_id": "estudiante_uid"}
    conv_ref.get.return_value = conv_doc

    chunk_guardado = {"documento_id": "d1", "nombre_doc": "FODA.pdf", "pagina": 2, "fragmento": "Texto FODA"}
    msg_prev = MagicMock()
    msg_prev.to_dict.return_value = {
        "pregunta": "¿Qué es FODA?", "respuesta": "¿Qué elementos conoces?",
        "usuario_id": "estudiante_uid", "creado_en": _TS(10.0),
        "chunks_usados": [chunk_guardado],
    }
    msg_ref = MagicMock()
    msg_ref.id = "msg-nuevo"
    mensajes_col = MagicMock()
    mensajes_col.where.return_value.stream.return_value = [msg_prev]
    mensajes_col.add.return_value = (None, msg_ref)

    def _col(name):
        col = MagicMock()
        dr = MagicMock()
        if name == "cursos":
            dr.get.return_value = curso_doc
            col.document.return_value = dr
        elif name == "usuarios":
            dr.get.return_value = user_doc
            col.document.return_value = dr
        elif name == "matriculas":
            dr.get.return_value = matricula_doc
            col.document.return_value = dr
        elif name == "conversaciones":
            col.document.return_value = conv_ref
        elif name == "mensajes":
            return mensajes_col
        return col

    db.collection.side_effect = _col
    app.dependency_overrides[get_current_user] = lambda: {"uid": "estudiante_uid"}
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as client:
        resp = client.post(
            "/cursos/curso1/chat",
            json={"pregunta": "ayúdame", "conversacion_id": "conv-fallback", "modo": "socratico"},
        )
    app.dependency_overrides.clear()

    assert resp.status_code == 200
    # generar_respuesta debe recibir los chunks del turno anterior, no lista vacía.
    chunks_recibidos = mock_gen.call_args.args[1]
    assert len(chunks_recibidos) == 1
    assert chunks_recibidos[0]["nombre_doc"] == "FODA.pdf"
    assert chunks_recibidos[0]["texto"] == "Texto FODA"


@patch("app.routers.chat.reescribir_consulta", side_effect=lambda p, h: p)
@patch("app.routers.chat.recuperar_chunks", return_value=[
    {"documento_id": "d2", "nombre_doc": "FODA.pdf", "pagina": 4,
     "texto": "Debilidades internas...", "score": 0.25},
])
@patch("app.routers.chat.generar_respuesta", return_value="Ejemplo con assessment center.")
def test_chat_fallback_si_seguimiento_contextual_tiene_chunks_debiles(
    mock_gen, mock_rag, mock_reescribir
):
    """Si el usuario pide 'el ultimo concepto' y el RAG trae basura debil,
    se prefiere el material usado en el turno anterior."""
    class _TS:
        def __init__(self, t):
            self._t = t
        def timestamp(self):
            return self._t

    db = MagicMock()
    curso_doc = MagicMock()
    curso_doc.exists = True
    curso_doc.to_dict.return_value = {"nombre": "Curso", "docente_id": "docente_uid", "activo": True}
    user_doc = MagicMock()
    user_doc.exists = True
    user_doc.to_dict.return_value = {"rol": "estudiante", "nombre": "Test"}
    matricula_doc = MagicMock()
    matricula_doc.exists = True

    conv_ref = MagicMock()
    conv_ref.id = "conv-assessment"
    conv_doc = MagicMock()
    conv_doc.exists = True
    conv_doc.to_dict.return_value = {"curso_id": "curso1", "usuario_id": "estudiante_uid"}
    conv_ref.get.return_value = conv_doc

    chunk_guardado = {
        "documento_id": "d1",
        "nombre_doc": "Assessment.pdf",
        "pagina": 2,
        "fragmento": "El assessment center usa situaciones simuladas para evaluar candidatos.",
    }
    msg_prev = MagicMock()
    msg_prev.to_dict.return_value = {
        "pregunta": "¿Que es un Assessment Center?",
        "respuesta": "Evalua candidatos con situaciones simuladas.",
        "usuario_id": "estudiante_uid",
        "creado_en": _TS(10.0),
        "chunks_usados": [chunk_guardado],
    }
    msg_ref = MagicMock()
    msg_ref.id = "msg-nuevo"
    mensajes_col = MagicMock()
    mensajes_col.where.return_value.stream.return_value = [msg_prev]
    mensajes_col.add.return_value = (None, msg_ref)

    def _col(name):
        col = MagicMock()
        dr = MagicMock()
        if name == "cursos":
            dr.get.return_value = curso_doc
            col.document.return_value = dr
        elif name == "usuarios":
            dr.get.return_value = user_doc
            col.document.return_value = dr
        elif name == "matriculas":
            dr.get.return_value = matricula_doc
            col.document.return_value = dr
        elif name == "conversaciones":
            col.document.return_value = conv_ref
        elif name == "mensajes":
            return mensajes_col
        return col

    db.collection.side_effect = _col
    app.dependency_overrides[get_current_user] = lambda: {"uid": "estudiante_uid"}
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as client:
        resp = client.post(
            "/cursos/curso1/chat",
            json={
                "pregunta": "Dame un ejemplo concreto del último concepto",
                "conversacion_id": "conv-assessment",
            },
        )
    app.dependency_overrides.clear()

    assert resp.status_code == 200
    chunks_recibidos = mock_gen.call_args.args[1]
    _, _, _, _, _, contexto_debil = mock_gen.call_args.args
    assert chunks_recibidos[0]["nombre_doc"] == "Assessment.pdf"
    assert "situaciones simuladas" in chunks_recibidos[0]["texto"]
    assert contexto_debil is False


@patch("app.routers.chat.reescribir_consulta", side_effect=lambda p, h: p)
@patch("app.routers.chat.recuperar_chunks", return_value=[])
@patch("app.routers.chat.generar_respuesta", return_value="No esta en el material.")
def test_chat_no_usa_fallback_historial_para_semana_explicita(
    mock_gen, mock_rag, mock_reescribir
):
    """Una pregunta nueva por semana no debe contaminarse con chunks previos."""
    class _TS:
        def __init__(self, t):
            self._t = t
        def timestamp(self):
            return self._t

    db = MagicMock()
    curso_doc = MagicMock()
    curso_doc.exists = True
    curso_doc.to_dict.return_value = {"nombre": "Curso", "docente_id": "docente_uid", "activo": True}
    user_doc = MagicMock()
    user_doc.exists = True
    user_doc.to_dict.return_value = {"rol": "estudiante", "nombre": "Test"}
    matricula_doc = MagicMock()
    matricula_doc.exists = True

    conv_ref = MagicMock()
    conv_ref.id = "conv-semana"
    conv_doc = MagicMock()
    conv_doc.exists = True
    conv_doc.to_dict.return_value = {"curso_id": "curso1", "usuario_id": "estudiante_uid"}
    conv_ref.get.return_value = conv_doc

    msg_prev = MagicMock()
    msg_prev.to_dict.return_value = {
        "pregunta": "¿Que es FODA?",
        "respuesta": "FODA...",
        "usuario_id": "estudiante_uid",
        "creado_en": _TS(10.0),
        "chunks_usados": [{
            "documento_id": "d1",
            "nombre_doc": "FODA.pdf",
            "pagina": 1,
            "fragmento": "Texto FODA",
        }],
    }
    msg_ref = MagicMock()
    msg_ref.id = "msg-nuevo"
    mensajes_col = MagicMock()
    mensajes_col.where.return_value.stream.return_value = [msg_prev]
    mensajes_col.add.return_value = (None, msg_ref)

    def _col(name):
        col = MagicMock()
        dr = MagicMock()
        if name == "cursos":
            dr.get.return_value = curso_doc
            col.document.return_value = dr
        elif name == "usuarios":
            dr.get.return_value = user_doc
            col.document.return_value = dr
        elif name == "matriculas":
            dr.get.return_value = matricula_doc
            col.document.return_value = dr
        elif name == "conversaciones":
            col.document.return_value = conv_ref
        elif name == "mensajes":
            return mensajes_col
        return col

    db.collection.side_effect = _col
    app.dependency_overrides[get_current_user] = lambda: {"uid": "estudiante_uid"}
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as client:
        resp = client.post(
            "/cursos/curso1/chat",
            json={
                "pregunta": "Resume los puntos clave de la semana 11",
                "conversacion_id": "conv-semana",
            },
        )
    app.dependency_overrides.clear()

    assert resp.status_code == 200
    data = resp.json()
    assert data["chunks_usados"] == []
    assert "semana 11" in data["respuesta"]
    mock_gen.assert_not_called()


@patch("app.routers.chat.recuperar_chunks", return_value=[
    {"documento_id": "d1", "nombre_doc": "Semana 11.pdf", "pagina": 2,
     "texto": "Contenido recuperado para diagnostico", "score": 0.88,
     "semana": 11, "metadata_match": True},
])
def test_diagnostico_rag_docente_devuelve_chunks(mock_rag):
    db = _mock_db_chat(rol_usuario="docente")
    app.dependency_overrides[get_current_user] = lambda: {"uid": "docente_uid"}
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as client:
        resp = client.post(
            "/cursos/curso1/rag/diagnostico",
            json={"pregunta": "Resume la semana 11"},
        )
    app.dependency_overrides.clear()

    assert resp.status_code == 200
    data = resp.json()
    assert data["semana_detectada"] == 11
    assert data["total_chunks"] == 1
    assert data["contexto_debil"] is False
    assert data["chunks"][0]["nombre_doc"] == "Semana 11.pdf"
