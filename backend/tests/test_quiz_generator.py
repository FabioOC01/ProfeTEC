"""Tests del parser/validador del generador de quizzes."""
from unittest.mock import MagicMock, patch

import pytest

from app.core.quiz_generator import (
    _parse_json_safe,
    _validar_pregunta,
    generar_preguntas,
)


def test_parse_json_safe_acepta_json_plano():
    data = _parse_json_safe('{"preguntas": []}')
    assert data == {"preguntas": []}


def test_parse_json_safe_acepta_fences_json():
    raw = '```json\n{"preguntas": [{"texto": "a"}]}\n```'
    data = _parse_json_safe(raw)
    assert data["preguntas"][0]["texto"] == "a"


def test_parse_json_safe_recupera_bloque_entre_llaves():
    raw = 'Aquí va el quiz:\n{"preguntas": [{"texto": "x"}]}\nGracias.'
    data = _parse_json_safe(raw)
    assert data["preguntas"][0]["texto"] == "x"


def test_validar_pregunta_normaliza_indice_invalido():
    p = _validar_pregunta({
        "texto": "Pregunta",
        "opciones": ["a", "b", "c"],
        "indice_correcto": 99,
    })
    assert p["indice_correcto"] == 0


def test_validar_pregunta_rechaza_menos_de_dos_opciones():
    with pytest.raises(ValueError):
        _validar_pregunta({"texto": "x", "opciones": ["solo una"]})


def test_validar_pregunta_recorta_texto_largo():
    largo = "a" * 1000
    p = _validar_pregunta({
        "texto": largo,
        "opciones": ["x", "y"],
        "indice_correcto": 0,
    })
    assert len(p["texto"]) == 600


@patch("app.core.quiz_generator.generar_texto", return_value='{"preguntas": []}')
@patch("app.core.quiz_generator.generar_json", return_value='{"preguntas": []}')
def test_generar_preguntas_sin_material_es_value_error(mock_json, mock_txt):
    """Si el curso no tiene chunks, debe abortar con un mensaje claro."""
    db = MagicMock()
    db.collection.return_value.where.return_value.limit.return_value.stream.return_value = []
    with pytest.raises(ValueError) as exc:
        generar_preguntas("curso1", tema=None, num_preguntas=3, db=db)
    assert "material" in str(exc.value).lower()


@patch("app.core.quiz_generator.generar_texto",
       return_value='{"preguntas": [{"texto": "?", "opciones": ["a", "b"], "indice_correcto": 0}]}')
@patch("app.core.quiz_generator.generar_json",
       return_value='{"preguntas": [{"texto": "?", "opciones": ["a", "b"], "indice_correcto": 0}]}')
def test_generar_preguntas_devuelve_preguntas_validadas(mock_json, mock_txt):
    db = MagicMock()
    chunk_doc = MagicMock()
    chunk_doc.to_dict.return_value = {
        "documento_id": "d1",
        "nombre_doc": "x.pdf",
        "pagina": 1,
        "texto": "contenido",
    }
    db.collection.return_value.where.return_value.limit.return_value.stream.return_value = [chunk_doc]
    preguntas = generar_preguntas("curso1", tema=None, num_preguntas=3, db=db)
    assert len(preguntas) == 1
    assert preguntas[0]["texto"] == "?"


@patch("app.core.quiz_generator.generar_texto",
       return_value='{"preguntas": [{"texto": "?", "opciones": ["a", "b"], "indice_correcto": 0}]}')
@patch("app.core.quiz_generator.generar_json",
       return_value='{"preguntas": [{"texto": "?", "opciones": ["a", "b"], "indice_correcto": 0}]}')
def test_generar_preguntas_filtra_por_rango_de_semana(mock_json, mock_txt):
    db = MagicMock()
    fuera = MagicMock()
    fuera.to_dict.return_value = {
        "documento_id": "d1",
        "nombre_doc": "semana1.pdf",
        "pagina": 1,
        "semana": 1,
        "texto": "omitido",
    }
    dentro = MagicMock()
    dentro.to_dict.return_value = {
        "documento_id": "d2",
        "nombre_doc": "semana3.pdf",
        "pagina": 1,
        "semana": 3,
        "texto": "incluido",
    }
    db.collection.return_value.where.return_value.limit.return_value.stream.return_value = [fuera, dentro]

    preguntas = generar_preguntas(
        "curso1",
        tema=None,
        num_preguntas=3,
        db=db,
        semana_desde=2,
        semana_hasta=4,
    )

    assert len(preguntas) == 1
    prompt = mock_json.call_args.args[0]
    assert "incluido" in prompt
    assert "omitido" not in prompt


@patch("app.core.quiz_generator.generar_texto", return_value="esto no es JSON")
@patch("app.core.quiz_generator.generar_json", return_value="")
def test_generar_preguntas_json_invalido_es_value_error(mock_json, mock_txt):
    db = MagicMock()
    chunk_doc = MagicMock()
    chunk_doc.to_dict.return_value = {
        "documento_id": "d1",
        "nombre_doc": "x.pdf",
        "pagina": 1,
        "texto": "contenido",
    }
    db.collection.return_value.where.return_value.limit.return_value.stream.return_value = [chunk_doc]
    with pytest.raises(ValueError):
        generar_preguntas("curso1", tema=None, num_preguntas=3, db=db)


@patch("app.core.quiz_generator.generar_texto",
       return_value='{"preguntas": [{"texto": "Recuperado", "opciones": ["x", "y"], "indice_correcto": 0}]}')
@patch("app.core.quiz_generator.generar_json", return_value="")
def test_generar_preguntas_reintenta_en_modo_texto_si_json_falla(mock_json, mock_txt):
    """Si el modo JSON viene vacío, el segundo intento en modo texto debe rescatar."""
    db = MagicMock()
    chunk_doc = MagicMock()
    chunk_doc.to_dict.return_value = {
        "documento_id": "d1",
        "nombre_doc": "x.pdf",
        "pagina": 1,
        "texto": "contenido",
    }
    db.collection.return_value.where.return_value.limit.return_value.stream.return_value = [chunk_doc]
    preguntas = generar_preguntas("curso1", tema=None, num_preguntas=3, db=db)
    assert len(preguntas) == 1
    assert preguntas[0]["texto"] == "Recuperado"
