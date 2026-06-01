"""Tests unitarios para el módulo RAG."""
from unittest.mock import MagicMock, patch


def _make_chunk_doc(texto="Texto de prueba", pagina=1, curso_id="curso1", semana=None):
    doc = MagicMock()
    doc.id = "chunk_id"
    doc.to_dict.return_value = {
        "curso_id": curso_id,
        "documento_id": "doc1",
        "nombre_doc": "apunte.pdf",
        "texto": texto,
        "embedding": [0.1, 0.2, 0.3],
        "pagina": pagina,
        "posicion": 0,
        "semana": semana,
    }
    return doc


def _make_db_with_chunks(chunks):
    db = MagicMock()
    query = db.collection.return_value.where.return_value
    query.limit.return_value = query
    query.stream.return_value = chunks
    return db, query


def test_detectar_semana_en_consulta():
    from app.core.rag import detectar_semana

    assert detectar_semana("Ayúdame a repasar la semana 2") == 2
    assert detectar_semana("repasar semana dos") == 2
    assert detectar_semana("quiero ver la 3ra semana") == 3
    assert detectar_semana("repasar árboles") is None


@patch("app.core.rag.embed_texts")
@patch("app.core.rag.cosine_similarity")
def test_recuperar_chunks_retorna_top_k_ordenados(mock_cos, mock_embed, monkeypatch):
    """Los chunks deben ordenarse por score descendente y respetar top_k."""
    monkeypatch.setattr("app.core.rag.settings.rag_backend", "firestore_scan")
    mock_embed.return_value = [[0.1, 0.2, 0.3]]
    mock_cos.side_effect = [0.9, 0.5, 0.7]  # scores no ordenados

    db, _query = _make_db_with_chunks([
        _make_chunk_doc("A"),
        _make_chunk_doc("B"),
        _make_chunk_doc("C"),
    ])

    from app.core.rag import recuperar_chunks
    result = recuperar_chunks("curso1", "¿qué es X?", db, top_k=2, score_minimo=0.0)

    assert len(result) == 2
    assert result[0]["score"] >= result[1]["score"]
    assert result[0]["score"] == 0.9


@patch("app.core.rag.embed_texts")
def test_recuperar_chunks_sin_documentos(mock_embed, monkeypatch):
    """Si no hay chunks, retorna lista vacía."""
    monkeypatch.setattr("app.core.rag.settings.rag_backend", "firestore_scan")
    mock_embed.return_value = [[0.1, 0.2, 0.3]]

    db, _query = _make_db_with_chunks([])

    from app.core.rag import recuperar_chunks
    result = recuperar_chunks("curso1", "pregunta", db)

    assert result == []


@patch("app.core.rag.embed_texts")
@patch("app.core.rag.cosine_similarity")
def test_recuperar_chunks_filtra_score_minimo(mock_cos, mock_embed, monkeypatch):
    """Chunks con score menor al mínimo no deben incluirse."""
    monkeypatch.setattr("app.core.rag.settings.rag_backend", "firestore_scan")
    mock_embed.return_value = [[0.1, 0.2, 0.3]]
    mock_cos.side_effect = [0.1, 0.05, 0.8]  # 2 bajo el umbral de 0.3

    db, _query = _make_db_with_chunks([
        _make_chunk_doc("A"),
        _make_chunk_doc("B"),
        _make_chunk_doc("C"),
    ])

    from app.core.rag import recuperar_chunks
    result = recuperar_chunks("curso1", "pregunta", db, top_k=5, score_minimo=0.3)

    assert len(result) == 1
    assert result[0]["score"] == 0.8


@patch("app.core.rag.embed_texts")
@patch("app.core.rag.cosine_similarity")
def test_recuperar_chunks_ignora_sin_embedding(mock_cos, mock_embed, monkeypatch):
    """Chunks sin campo 'embedding' deben ignorarse."""
    monkeypatch.setattr("app.core.rag.settings.rag_backend", "firestore_scan")
    mock_embed.return_value = [[0.1, 0.2, 0.3]]
    mock_cos.return_value = 0.9

    sin_embedding = MagicMock()
    sin_embedding.to_dict.return_value = {"curso_id": "c", "texto": "X", "pagina": 1}

    db, _query = _make_db_with_chunks([sin_embedding])

    from app.core.rag import recuperar_chunks
    result = recuperar_chunks("curso1", "pregunta", db)

    assert result == []
    mock_cos.assert_not_called()


@patch("app.core.rag.embed_texts")
@patch("app.core.rag.cosine_similarity")
def test_recuperar_chunks_limita_escaneo_configurable(mock_cos, mock_embed, monkeypatch):
    """El escaneo Firestore debe tener limite para no leer cursos completos sin control."""
    monkeypatch.setattr("app.core.rag.settings.rag_backend", "firestore_scan")
    mock_embed.return_value = [[0.1, 0.2, 0.3]]
    mock_cos.return_value = 0.9
    db, query = _make_db_with_chunks([_make_chunk_doc("A")])

    from app.core.rag import recuperar_chunks
    result = recuperar_chunks("curso1", "pregunta", db, max_chunks_scan=25)

    assert len(result) == 1
    query.limit.assert_called_once_with(25)


@patch("app.core.rag.embed_texts")
@patch("app.core.rag.cosine_similarity")
def test_recuperar_chunks_filtra_por_semana_y_relaja_score(mock_cos, mock_embed, monkeypatch):
    """Si la consulta menciona semana exacta, debe traer chunks de esa semana
    aunque el embedding de "repasar semana 2" tenga baja similitud.
    """
    monkeypatch.setattr("app.core.rag.settings.rag_backend", "firestore_scan")
    monkeypatch.setattr("app.core.rag.settings.rag_score_confianza", 0.6)
    mock_embed.return_value = [[0.1, 0.2, 0.3]]
    mock_cos.side_effect = [0.05, 0.04]

    db, _query = _make_db_with_chunks([
        _make_chunk_doc("Semana 1", semana=1),
        _make_chunk_doc("Semana 2 A", semana=2),
        _make_chunk_doc("Semana 2 B", semana=2),
    ])

    from app.core.rag import recuperar_chunks

    result = recuperar_chunks(
        "curso1",
        "Ayúdame a repasar la semana 2",
        db,
        top_k=5,
        score_minimo=0.3,
    )

    assert [r["texto"] for r in result] == ["Semana 2 A", "Semana 2 B"]
    assert all(r["semana"] == 2 for r in result)
    assert all(r["metadata_match"] is True for r in result)
    assert all(r["score"] >= 0.6 for r in result)


@patch("app.core.rag.embed_texts")
@patch("app.core.bigquery_rag.search_chunks")
def test_recuperar_chunks_usa_bigquery_vector(mock_search, mock_embed, monkeypatch):
    mock_embed.return_value = [[0.1, 0.2, 0.3]]
    mock_search.return_value = [{"texto": "A", "score": 0.9}]
    monkeypatch.setattr("app.core.rag.settings.rag_backend", "bigquery_vector")

    from app.core.rag import recuperar_chunks

    result = recuperar_chunks("curso1", "pregunta", MagicMock(), top_k=4, score_minimo=0.2)

    assert result == [{"texto": "A", "score": 0.9}]
    mock_search.assert_called_once_with("curso1", [0.1, 0.2, 0.3], 4, 0.2, semana=None)


@patch("app.core.rag.embed_texts")
@patch("app.core.bigquery_rag.search_chunks", side_effect=RuntimeError("bq down"))
@patch("app.core.rag.cosine_similarity")
def test_recuperar_chunks_bigquery_fallback_firestore(mock_cos, mock_search, mock_embed, monkeypatch):
    mock_embed.return_value = [[0.1, 0.2, 0.3]]
    mock_cos.return_value = 0.9
    monkeypatch.setattr("app.core.rag.settings.rag_backend", "bigquery_vector")
    db, query = _make_db_with_chunks([_make_chunk_doc("A")])

    from app.core.rag import recuperar_chunks

    result = recuperar_chunks("curso1", "pregunta", db)

    assert len(result) == 1
    assert result[0]["texto"] == "A"
    mock_search.assert_called_once()
    query.limit.assert_called_once()


@patch("app.core.rag.embed_texts")
@patch("app.core.bigquery_rag.search_chunks", return_value=[])
@patch("app.core.rag.cosine_similarity")
def test_recuperar_chunks_semana_exacta_fallback_firestore_si_bigquery_vacio(
    mock_cos, mock_search, mock_embed, monkeypatch
):
    """Si BigQuery esta desfasado para una semana, Firestore aun puede resolverla."""
    mock_embed.return_value = [[0.1, 0.2, 0.3]]
    mock_cos.return_value = 0.05
    monkeypatch.setattr("app.core.rag.settings.rag_backend", "bigquery_vector")
    monkeypatch.setattr("app.core.rag.settings.rag_score_confianza", 0.6)
    db, query = _make_db_with_chunks([
        _make_chunk_doc("Semana 3", semana=3),
        _make_chunk_doc("Semana 11", semana=11),
    ])

    from app.core.rag import recuperar_chunks

    result = recuperar_chunks("curso1", "Resume los puntos clave de la semana 11", db)

    assert [r["texto"] for r in result] == ["Semana 11"]
    assert result[0]["semana"] == 11
    mock_search.assert_called_once()
    query.limit.assert_called_once()
