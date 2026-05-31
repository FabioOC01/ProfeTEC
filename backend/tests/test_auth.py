"""Tests del módulo de autenticación — Sprint 1 (RF-01, RF-02, RF-03)."""
from unittest.mock import MagicMock

from tests.conftest import DOCENTE_CLAIMS, _make_doc, _make_missing_doc


class TestAuthMe:
    def test_primer_login_crea_usuario_y_pide_onboarding(self, client_nuevo_usuario):
        """RF-01 + RF-02: primer login crea perfil y retorna needs_onboarding=True."""
        response = client_nuevo_usuario.post("/auth/me")
        assert response.status_code == 200
        body = response.json()
        assert body["needs_onboarding"] is True
        assert body["usuario"]["email"] == DOCENTE_CLAIMS["email"]

    def test_login_existente_sin_rol_pide_onboarding(self, client_sin_rol):
        """RF-02: usuario con rol=None siempre vuelve a onboarding."""
        response = client_sin_rol.post("/auth/me")
        assert response.status_code == 200
        assert response.json()["needs_onboarding"] is True

    def test_login_con_rol_no_pide_onboarding(self, client_docente):
        """RF-02: usuario con rol asignado no requiere onboarding."""
        response = client_docente.post("/auth/me")
        assert response.status_code == 200
        assert response.json()["needs_onboarding"] is False

    def test_rechaza_correo_no_institucional(self, db_mock, monkeypatch):
        """Seguridad: solo se aceptan correos del dominio institucional.

        Fuerza el dominio permitido a tecsup.edu.pe para que la prueba sea
        independiente de la configuración local del .env (que puede tener "*").
        """
        from app.main import app
        from app.core.auth import get_current_user
        from app.core.firestore_client import get_db
        from app.config import settings
        from fastapi.testclient import TestClient

        monkeypatch.setattr(settings, "allowed_email_domains", "tecsup.edu.pe")

        app.dependency_overrides[get_current_user] = lambda: {
            "uid": "externo",
            "email": "persona@example.com",
            "name": "Persona Externa",
        }
        app.dependency_overrides[get_db] = lambda: db_mock
        with TestClient(app) as c:
            response = c.post("/auth/me")
        app.dependency_overrides.clear()

        assert response.status_code == 403


class TestSetRol:
    def test_asignar_rol_docente(self, client_sin_rol, db_mock):
        """RF-02: usuario sin rol puede elegir 'docente'.
        El fixture client_sin_rol ya configura get() para retornar rol=None;
        el router modifica data localmente y no vuelve a llamar get().
        """
        db_mock.collection.return_value.document.return_value.update.return_value = None

        response = client_sin_rol.patch("/auth/me/rol", json={"rol": "docente"})
        assert response.status_code == 200
        body = response.json()
        assert body["usuario"]["rol"] == "docente"
        assert body["needs_onboarding"] is False

    def test_asignar_rol_crea_usuario_si_no_existe(self):
        """Robustez: si /auth/me no creo el doc, el onboarding lo crea al elegir rol."""
        from app.main import app
        from app.core.auth import get_current_user
        from app.core.firestore_client import get_db
        from fastapi.testclient import TestClient

        db = MagicMock()
        ref = MagicMock()
        ref.get.return_value = _make_missing_doc()
        db.collection.return_value.document.return_value = ref

        claims = {
            "uid": "uid-estudiante-nuevo",
            "email": "estudiante@tecsup.edu.pe",
            "name": "Estudiante Nuevo",
            "picture": None,
        }
        app.dependency_overrides[get_current_user] = lambda: claims
        app.dependency_overrides[get_db] = lambda: db
        with TestClient(app) as c:
            response = c.patch("/auth/me/rol", json={"rol": "estudiante"})
        app.dependency_overrides.clear()

        assert response.status_code == 200
        assert response.json()["usuario"]["rol"] == "estudiante"
        ref.set.assert_called_once()

    def test_docente_debe_estar_autorizado(self):
        """Seguridad: no cualquier usuario institucional puede ser docente."""
        from app.main import app
        from app.core.auth import get_current_user
        from app.core.firestore_client import get_db
        from fastapi.testclient import TestClient

        db = MagicMock()
        user_doc = _make_doc(DOCENTE_CLAIMS["uid"], {
            "email": DOCENTE_CLAIMS["email"],
            "nombre": DOCENTE_CLAIMS["name"],
            "foto_url": None,
            "rol": None,
        })
        docente_doc = _make_missing_doc()

        def _collection(name):
            col = MagicMock()
            doc_ref = MagicMock()
            if name == "usuarios":
                doc_ref.get.return_value = user_doc
            elif name == "docentes_autorizados":
                doc_ref.get.return_value = docente_doc
            col.document.return_value = doc_ref
            return col

        db.collection.side_effect = _collection
        app.dependency_overrides[get_current_user] = lambda: DOCENTE_CLAIMS
        app.dependency_overrides[get_db] = lambda: db
        with TestClient(app) as c:
            response = c.patch("/auth/me/rol", json={"rol": "docente"})
        app.dependency_overrides.clear()

        assert response.status_code == 403

    def test_rol_invalido_retorna_422(self, client_sin_rol):
        """RF-03 (control): rol fuera de ['docente','estudiante'] falla validación."""
        response = client_sin_rol.patch("/auth/me/rol", json={"rol": "admin"})
        assert response.status_code == 422

    def test_cambiar_rol_ya_asignado_retorna_400(self, client_docente):
        """Seguridad: no se puede cambiar el rol una vez asignado."""
        response = client_docente.patch("/auth/me/rol", json={"rol": "estudiante"})
        assert response.status_code == 400
