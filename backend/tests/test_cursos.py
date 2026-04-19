"""Tests del módulo de cursos — Sprint 1 (RF-05)."""
from unittest.mock import MagicMock, patch

from tests.conftest import DOCENTE_CLAIMS, _make_doc, _make_missing_doc


CURSO_ID = "curso-test-001"
CURSO_DATA = {
    "nombre": "Algoritmos y Estructuras de Datos",
    "descripcion": "Curso de quinto ciclo.",
    "docente_id": DOCENTE_CLAIMS["uid"],
    "docente_nombre": DOCENTE_CLAIMS["name"],
    "codigo": "ABC123",
    "activo": True,
}


class TestCrearCurso:
    def test_docente_puede_crear_curso(self, client_docente, db_mock):
        """RF-05: docente autenticado crea un curso exitosamente."""
        ref_mock = MagicMock()
        ref_mock.id = CURSO_ID
        db_mock.collection.return_value.add.return_value = (None, ref_mock)

        response = client_docente.post(
            "/cursos",
            json={"nombre": "Algoritmos I", "descripcion": "Intro."},
        )
        assert response.status_code == 201
        body = response.json()
        assert body["nombre"] == "Algoritmos I"
        assert body["docente_id"] == DOCENTE_CLAIMS["uid"]
        assert len(body["codigo"]) == 6

    def test_nombre_vacio_retorna_422(self, client_docente):
        """Validación: nombre vacío falla antes de llegar a Firestore."""
        response = client_docente.post("/cursos", json={"nombre": "   "})
        assert response.status_code == 422

    def test_estudiante_no_puede_crear_curso(self, db_mock):
        """RF-03 (control): estudiante recibe 403 al intentar crear curso."""
        from app.main import app
        from app.core.auth import get_current_user
        from app.core.firestore_client import get_db
        from fastapi.testclient import TestClient

        estudiante_claims = {
            "uid": "uid-est",
            "email": "est@tecsup.edu.pe",
            "name": "Est",
        }
        db_mock.collection.return_value.document.return_value.get.return_value = _make_doc(
            "uid-est", {"email": "est@tecsup.edu.pe", "nombre": "Est", "rol": "estudiante"}
        )

        app.dependency_overrides[get_current_user] = lambda: estudiante_claims
        app.dependency_overrides[get_db] = lambda: db_mock
        with TestClient(app) as c:
            response = c.post("/cursos", json={"nombre": "Curso X"})
        app.dependency_overrides.clear()

        assert response.status_code == 403


class TestListarCursos:
    def test_listar_cursos_del_docente(self, client_docente, db_mock):
        """RF-05: docente obtiene su lista de cursos."""
        curso_doc = _make_doc(CURSO_ID, CURSO_DATA)
        db_mock.collection.return_value.where.return_value.where.return_value.stream.return_value = [curso_doc]
        db_mock.collection.return_value.where.return_value.stream.return_value = [curso_doc]

        response = client_docente.get("/cursos")
        assert response.status_code == 200
        cursos = response.json()
        assert isinstance(cursos, list)


class TestEditarCurso:
    def test_docente_edita_su_curso(self, client_docente, db_mock):
        """RF-05: docente actualiza nombre y descripción."""
        ref_mock = db_mock.collection.return_value.document.return_value
        # Primera llamada: get usuario; segunda: get curso; tercera: get after update
        ref_mock.get.side_effect = [
            _make_doc(DOCENTE_CLAIMS["uid"], {
                "email": DOCENTE_CLAIMS["email"], "nombre": DOCENTE_CLAIMS["name"], "rol": "docente"
            }),
            _make_doc(CURSO_ID, CURSO_DATA),
            _make_doc(CURSO_ID, {**CURSO_DATA, "nombre": "Algoritmos II"}),
        ]
        ref_mock.update.return_value = None

        response = client_docente.patch(f"/cursos/{CURSO_ID}", json={"nombre": "Algoritmos II"})
        assert response.status_code == 200
        assert response.json()["nombre"] == "Algoritmos II"


class TestEliminarCurso:
    def test_docente_elimina_su_curso(self, client_docente, db_mock):
        """RF-05: docente puede eliminar un curso propio."""
        ref_mock = db_mock.collection.return_value.document.return_value
        ref_mock.get.side_effect = [
            _make_doc(DOCENTE_CLAIMS["uid"], {
                "email": DOCENTE_CLAIMS["email"], "nombre": DOCENTE_CLAIMS["name"], "rol": "docente"
            }),
            _make_doc(CURSO_ID, CURSO_DATA),
        ]
        ref_mock.delete.return_value = None

        response = client_docente.delete(f"/cursos/{CURSO_ID}")
        assert response.status_code == 204

    def test_eliminar_curso_inexistente_retorna_404(self, client_docente, db_mock):
        """Edge case: eliminar curso que no existe retorna 404."""
        ref_mock = db_mock.collection.return_value.document.return_value
        ref_mock.get.side_effect = [
            _make_doc(DOCENTE_CLAIMS["uid"], {
                "email": DOCENTE_CLAIMS["email"], "nombre": DOCENTE_CLAIMS["name"], "rol": "docente"
            }),
            _make_missing_doc(),
        ]

        response = client_docente.delete("/cursos/no-existe")
        assert response.status_code == 404
