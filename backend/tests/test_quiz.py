"""Tests del módulo de quizzes (RF-20..RF-23)."""
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.auth import get_current_user
from app.core.firestore_client import get_db


PREGUNTAS_FAKE = [
    {
        "texto": "¿Qué es un árbol binario?",
        "opciones": ["A1", "A2", "A3", "A4"],
        "indice_correcto": 1,
        "explicacion": "Por X.",
        "nombre_doc": "apunte.pdf",
        "pagina": 3,
    },
    {
        "texto": "¿Para qué sirve la recursión?",
        "opciones": ["B1", "B2", "B3", "B4"],
        "indice_correcto": 0,
        "explicacion": "Por Y.",
        "nombre_doc": "apunte.pdf",
        "pagina": 5,
    },
    {
        "texto": "¿Cuál es la complejidad de búsqueda binaria?",
        "opciones": ["O(1)", "O(n)", "O(log n)", "O(n log n)"],
        "indice_correcto": 2,
        "explicacion": "Por Z.",
        "nombre_doc": "apunte.pdf",
        "pagina": 7,
    },
]


def _mock_db_quizzes(rol="docente", quiz_existe=True, intentos_data=None):
    """Construye un MagicMock de Firestore para tests de quizzes."""
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
    user_doc.to_dict.return_value = {"rol": rol, "nombre": "Test"}

    matricula_doc = MagicMock()
    matricula_doc.exists = True

    quiz_doc = MagicMock()
    quiz_doc.exists = quiz_existe
    quiz_doc.id = "quiz1"
    quiz_doc.to_dict.return_value = {
        "curso_id": "curso1",
        "docente_id": "docente_uid",
        "titulo": "Quiz de prueba",
        "tema": "árboles",
        "preguntas": PREGUNTAS_FAKE,
    }

    intentos_data = intentos_data or []

    quiz_added_ref = MagicMock()
    quiz_added_ref.id = "quiz_nuevo"
    intento_added_ref = MagicMock()
    intento_added_ref.id = "intento1"

    def _collection(name):
        col = MagicMock()
        if name == "cursos":
            doc_ref = MagicMock()
            doc_ref.get.return_value = curso_doc
            col.document.return_value = doc_ref
        elif name == "usuarios":
            doc_ref = MagicMock()
            doc_ref.get.return_value = user_doc
            col.document.return_value = doc_ref
        elif name == "matriculas":
            doc_ref = MagicMock()
            doc_ref.get.return_value = matricula_doc
            col.document.return_value = doc_ref
        elif name == "quizzes":
            doc_ref = MagicMock()
            doc_ref.get.return_value = quiz_doc
            doc_ref.delete.return_value = None
            col.document.return_value = doc_ref
            col.add.return_value = (None, quiz_added_ref)
            col.where.return_value.stream.return_value = [quiz_doc] if quiz_existe else []
        elif name == "quiz_intentos":
            col.add.return_value = (None, intento_added_ref)
            # Encadenado: where(...).where(...).stream() y where(...).stream()
            stream_intentos = [
                _make_intento_doc(i, d) for i, d in enumerate(intentos_data)
            ]
            wq = MagicMock()
            wq.where.return_value.stream.return_value = stream_intentos
            wq.stream.return_value = stream_intentos
            col.where.return_value = wq
        return col

    db.collection.side_effect = _collection
    return db


def _make_intento_doc(i, data):
    doc = MagicMock()
    doc.id = f"intento{i}"
    doc.exists = True
    doc.to_dict.return_value = data
    return doc


@pytest.fixture
def client_docente_quiz():
    db = _mock_db_quizzes(rol="docente")
    app.dependency_overrides[get_current_user] = lambda: {"uid": "docente_uid", "name": "Prof"}
    app.dependency_overrides[get_db] = lambda: db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def client_estudiante_quiz():
    db = _mock_db_quizzes(rol="estudiante")
    app.dependency_overrides[get_current_user] = lambda: {
        "uid": "estudiante_uid",
        "name": "Estu",
        "email": "estu@tecsup.edu.pe",
    }
    app.dependency_overrides[get_db] = lambda: db
    yield TestClient(app)
    app.dependency_overrides.clear()


# ── Crear quiz ───────────────────────────────────────────────────────────────

@patch("app.routers.quiz.generar_preguntas", return_value=PREGUNTAS_FAKE)
def test_crear_quiz_como_docente_ok(mock_gen, client_docente_quiz):
    resp = client_docente_quiz.post(
        "/cursos/curso1/quizzes",
        json={"titulo": "Quiz de prueba", "tema": "árboles", "num_preguntas": 3},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["titulo"] == "Quiz de prueba"
    assert len(data["preguntas"]) == 3
    # El docente sí ve indice_correcto
    assert "indice_correcto" in data["preguntas"][0]


@patch("app.routers.quiz.generar_preguntas", return_value=PREGUNTAS_FAKE)
def test_crear_quiz_como_estudiante_es_403(mock_gen, client_estudiante_quiz):
    resp = client_estudiante_quiz.post(
        "/cursos/curso1/quizzes",
        json={"titulo": "Quiz", "num_preguntas": 3},
    )
    assert resp.status_code == 403


@patch("app.routers.quiz.generar_preguntas", side_effect=ValueError("Sin material"))
def test_crear_quiz_sin_material_es_400(mock_gen, client_docente_quiz):
    resp = client_docente_quiz.post(
        "/cursos/curso1/quizzes",
        json={"titulo": "Quiz", "num_preguntas": 3},
    )
    assert resp.status_code == 400
    assert "Sin material" in resp.json()["detail"]


def test_crear_quiz_titulo_vacio_es_422(client_docente_quiz):
    resp = client_docente_quiz.post(
        "/cursos/curso1/quizzes",
        json={"titulo": "", "num_preguntas": 3},
    )
    assert resp.status_code == 422


def test_crear_quiz_num_preguntas_fuera_de_rango_es_422(client_docente_quiz):
    resp = client_docente_quiz.post(
        "/cursos/curso1/quizzes",
        json={"titulo": "Quiz", "num_preguntas": 20},
    )
    assert resp.status_code == 422


@patch("app.routers.quiz.generar_preguntas", return_value=PREGUNTAS_FAKE)
def test_crear_quiz_envia_rango_de_semanas_al_generador(mock_gen, client_docente_quiz):
    resp = client_docente_quiz.post(
        "/cursos/curso1/quizzes",
        json={
            "titulo": "Quiz semanas",
            "num_preguntas": 3,
            "semana_desde": 1,
            "semana_hasta": 4,
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["semana_desde"] == 1
    assert data["semana_hasta"] == 4
    assert mock_gen.call_args.kwargs["semana_desde"] == 1
    assert mock_gen.call_args.kwargs["semana_hasta"] == 4


def test_crear_quiz_rechaza_rango_de_semanas_invalido(client_docente_quiz):
    resp = client_docente_quiz.post(
        "/cursos/curso1/quizzes",
        json={
            "titulo": "Quiz semanas",
            "num_preguntas": 3,
            "semana_desde": 5,
            "semana_hasta": 2,
        },
    )
    assert resp.status_code == 422


# ── Detalle: docente vs estudiante ────────────────────────────────────────────

def test_detalle_quiz_docente_ve_respuesta_correcta(client_docente_quiz):
    resp = client_docente_quiz.get("/cursos/curso1/quizzes/quiz1")
    assert resp.status_code == 200
    data = resp.json()
    assert "indice_correcto" in data["preguntas"][0]


def test_detalle_quiz_estudiante_no_ve_respuesta_correcta(client_estudiante_quiz):
    resp = client_estudiante_quiz.get("/cursos/curso1/quizzes/quiz1")
    assert resp.status_code == 200
    data = resp.json()
    # PreguntaParaResponder no incluye indice_correcto
    primera = data["preguntas"][0]
    assert "indice_correcto" not in primera
    assert "explicacion" not in primera
    assert "opciones" in primera


# ── Intentos ─────────────────────────────────────────────────────────────────

def test_intento_correcto_devuelve_porcentaje(client_estudiante_quiz):
    resp = client_estudiante_quiz.post(
        "/cursos/curso1/quizzes/quiz1/intentos",
        json={"respuestas": [1, 0, 2]},  # todas correctas
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["correctas"] == 3
    assert data["total_preguntas"] == 3
    assert data["porcentaje"] == 1.0
    assert len(data["detalle"]) == 3
    assert all(d["es_correcta"] for d in data["detalle"])


def test_intento_parcialmente_correcto(client_estudiante_quiz):
    resp = client_estudiante_quiz.post(
        "/cursos/curso1/quizzes/quiz1/intentos",
        json={"respuestas": [1, 0, 0]},  # primeras 2 correctas, última incorrecta
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["correctas"] == 2
    assert data["detalle"][2]["es_correcta"] is False


def test_intento_cantidad_respuestas_invalida_es_400(client_estudiante_quiz):
    resp = client_estudiante_quiz.post(
        "/cursos/curso1/quizzes/quiz1/intentos",
        json={"respuestas": [1, 0]},  # faltan respuestas
    )
    assert resp.status_code == 400


def test_intento_respuesta_fuera_de_rango_es_400(client_estudiante_quiz):
    resp = client_estudiante_quiz.post(
        "/cursos/curso1/quizzes/quiz1/intentos",
        json={"respuestas": [1, 0, 99]},
    )
    assert resp.status_code == 400


def test_intento_como_docente_es_403(client_docente_quiz):
    resp = client_docente_quiz.post(
        "/cursos/curso1/quizzes/quiz1/intentos",
        json={"respuestas": [1, 0, 2]},
    )
    assert resp.status_code == 403


# ── Quiz no existe ────────────────────────────────────────────────────────────

def test_detalle_quiz_inexistente_es_404():
    db = _mock_db_quizzes(rol="docente", quiz_existe=False)
    app.dependency_overrides[get_current_user] = lambda: {"uid": "docente_uid"}
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as c:
        resp = c.get("/cursos/curso1/quizzes/no-existe")
    app.dependency_overrides.clear()
    assert resp.status_code == 404


def test_quiz_de_otro_curso_es_403():
    """Si el quiz pertenece a otro curso, debe devolver 403."""
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
    user_doc.to_dict.return_value = {"rol": "docente"}

    quiz_doc = MagicMock()
    quiz_doc.exists = True
    quiz_doc.id = "quiz1"
    quiz_doc.to_dict.return_value = {
        "curso_id": "OTRO_curso",  # pertenece a otro curso
        "docente_id": "docente_uid",
        "titulo": "Q",
        "preguntas": PREGUNTAS_FAKE,
    }

    def _col(name):
        col = MagicMock()
        if name == "cursos":
            doc_ref = MagicMock()
            doc_ref.get.return_value = curso_doc
            col.document.return_value = doc_ref
        elif name == "usuarios":
            doc_ref = MagicMock()
            doc_ref.get.return_value = user_doc
            col.document.return_value = doc_ref
        elif name == "quizzes":
            doc_ref = MagicMock()
            doc_ref.get.return_value = quiz_doc
            col.document.return_value = doc_ref
        return col

    db.collection.side_effect = _col

    app.dependency_overrides[get_current_user] = lambda: {"uid": "docente_uid"}
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as c:
        resp = c.get("/cursos/curso1/quizzes/quiz1")
    app.dependency_overrides.clear()

    assert resp.status_code == 403
