"""Tests unitarios para utilidades de generación con Gemini."""
from unittest.mock import patch

from app.core.gemini import (
    _limpiar_citas_duplicadas,
    es_peticion_practica,
    es_rendicion,
    es_seguimiento_contextual,
    reescribir_consulta,
    respuesta_social,
)


def test_reescribir_sin_historial_devuelve_pregunta_original():
    """Sin historial no hay nada que contextualizar: devuelve la pregunta tal cual
    y no invoca al modelo."""
    with patch("app.core.gemini.generar_texto") as mock_gen:
        assert reescribir_consulta("¿Qué es FODA?", None) == "¿Qué es FODA?"
        assert reescribir_consulta("¿Qué es FODA?", []) == "¿Qué es FODA?"
        mock_gen.assert_not_called()


@patch("app.core.gemini.generar_texto",
       return_value="  Elementos del análisis FODA además de fortalezas y debilidades  ")
def test_reescribir_con_historial_usa_modelo_y_limpia(mock_gen):
    """Con historial, reescribe el seguimiento corto en una consulta autónoma."""
    historial = [{
        "pregunta": "¿Qué significa FODA?",
        "respuesta": "¿Qué otros elementos se mencionan además de fortalezas y debilidades?",
    }]
    resultado = reescribir_consulta("No lo sé, ayúdame", historial)
    assert resultado == "Elementos del análisis FODA además de fortalezas y debilidades"
    mock_gen.assert_called_once()


@patch("app.core.gemini.generar_texto", return_value="")
def test_reescribir_respuesta_vacia_cae_a_original(mock_gen):
    """Si el modelo no devuelve nada, se usa la pregunta original (nunca rompe el chat)."""
    historial = [{"pregunta": "p", "respuesta": "r"}]
    assert reescribir_consulta("No lo sé", historial) == "No lo sé"


@patch("app.core.gemini.generar_texto", return_value="x" * 400)
def test_reescribir_respuesta_desbordada_cae_a_original(mock_gen):
    """Una reescritura desproporcionadamente larga se descarta por seguridad."""
    historial = [{"pregunta": "p", "respuesta": "r"}]
    assert reescribir_consulta("No lo sé", historial) == "No lo sé"


@patch("app.core.gemini.generar_texto", side_effect=RuntimeError("vertex down"))
def test_reescribir_ante_error_cae_a_original(mock_gen):
    """Un fallo del modelo no debe propagarse: se usa la pregunta original."""
    historial = [{"pregunta": "p", "respuesta": "r"}]
    assert reescribir_consulta("No lo sé", historial) == "No lo sé"


@patch("app.core.gemini.generar_texto")
def test_reescribir_selectiva_omite_llamada_para_preguntas_largas(mock_gen):
    """Preguntas largas y específicas no llaman al modelo (ya son autónomas)."""
    historial = [{"pregunta": "p", "respuesta": "r"}]
    resultado = reescribir_consulta(
        "¿Cuál es la diferencia entre una oportunidad y una fortaleza en FODA?",
        historial,
    )
    # La pregunta tiene más de 5 palabras y no contiene términos vagos.
    assert resultado == "¿Cuál es la diferencia entre una oportunidad y una fortaleza en FODA?"
    mock_gen.assert_not_called()


@patch("app.core.gemini.generar_texto",
       return_value="Ejemplo concreto de assessment center en seleccion de personal")
def test_reescribir_seguimiento_largo_con_ultimo_concepto(mock_gen):
    """Un seguimiento largo con 'ultimo concepto' tambien debe usar historial."""
    historial = [{
        "pregunta": "¿Que es un Assessment Center?",
        "respuesta": "El assessment center evalua candidatos con situaciones simuladas.",
    }]
    resultado = reescribir_consulta("Dame un ejemplo concreto del último concepto", historial)
    assert resultado == "Ejemplo concreto de assessment center en seleccion de personal"
    mock_gen.assert_called_once()


def test_detecta_seguimientos_contextuales_y_peticiones_practicas():
    assert es_seguimiento_contextual("Dame un ejemplo concreto del último concepto") is True
    assert es_seguimiento_contextual("¿Cuál es la definición de empleabilidad?") is False
    assert es_peticion_practica("Dame tips para mi CB") is True
    assert es_peticion_practica("Que el reclutador me note") is True


def test_limpiar_citas_duplicadas_colapsa_repeticiones():
    texto = "Tema explicado [📄 doc.pdf, pág. 1] | [📄 doc.pdf, pág. 1]"
    assert _limpiar_citas_duplicadas(texto) == "Tema explicado [📄 doc.pdf, pág. 1]"


def test_respuesta_social_maneja_gracias_sin_rag():
    assert respuesta_social("gracias", "directo").startswith("De nada")
    assert "practicando" in respuesta_social("muchas gracias", "socratico")
    assert respuesta_social("¿Qué es FODA?", "directo") is None


def test_respuesta_social_maneja_saludos_identidad_y_funcionamiento():
    assert respuesta_social("hola", "directo").startswith("Hola")
    assert "tutor virtual" in respuesta_social("¿Quién eres?", "directo")
    assert "proyecto ProfeTEC.IA" in respuesta_social("¿Quién te creó?", "directo")
    assert "documentos subidos" in respuesta_social("¿Cómo funcionas?", "directo")


# ── Tests de es_rendicion ─────────────────────────────────────────────────────

def test_es_rendicion_detecta_frases_conocidas():
    assert es_rendicion("no lo sé") is True
    assert es_rendicion("ayúdame") is True
    assert es_rendicion("me rindo") is True
    assert es_rendicion("dame la respuesta") is True
    assert es_rendicion("no tengo idea") is True


def test_es_rendicion_no_falsos_positivos():
    assert es_rendicion("¿Qué es el análisis FODA?") is False
    assert es_rendicion("Explícame las oportunidades del FODA") is False
    assert es_rendicion("¿Cuáles son las fortalezas internas?") is False


def test_es_rendicion_case_insensitive():
    assert es_rendicion("NO LO SÉ") is True
    assert es_rendicion("AYÚDAME") is True
