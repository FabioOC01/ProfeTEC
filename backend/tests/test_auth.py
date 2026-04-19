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

    def test_rol_invalido_retorna_422(self, client_sin_rol):
        """RF-03 (control): rol fuera de ['docente','estudiante'] falla validación."""
        response = client_sin_rol.patch("/auth/me/rol", json={"rol": "admin"})
        assert response.status_code == 422

    def test_cambiar_rol_ya_asignado_retorna_400(self, client_docente):
        """Seguridad: no se puede cambiar el rol una vez asignado."""
        response = client_docente.patch("/auth/me/rol", json={"rol": "estudiante"})
        assert response.status_code == 400
