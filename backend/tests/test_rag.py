"""Tests unitarios para el módulo RAG."""
from unittest.mock import MagicMock, patch


def _make_chunk_doc(texto="Texto de prueba", pagina=1, curso_id="curso1"):
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
    }
    return doc


def _make_db_with_chunks(chunks):
    db = MagicMock()
    query = db.collection.return_value.where.return_value
    query.limit.return_value = query
    query.stream.return_value = chunks
    return db, query


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
@patch("app.core.bigquery_rag.search_chunks")
def test_recuperar_chunks_usa_bigquery_vector(mock_search, mock_embed, monkeypatch):
    mock_embed.return_value = [[0.1, 0.2, 0.3]]
    mock_search.return_value = [{"texto": "A", "score": 0.9}]
    monkeypatch.setattr("app.core.rag.settings.rag_backend", "bigquery_vector")

    from app.core.rag import recuperar_chunks

    result = recuperar_chunks("curso1", "pregunta", MagicMock(), top_k=4, score_minimo=0.2)

    assert result == [{"texto": "A", "score": 0.9}]
    mock_search.assert_called_once_with("curso1", [0.1, 0.2, 0.3], 4, 0.2)


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
