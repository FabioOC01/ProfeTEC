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


@patch("app.core.rag.embed_texts")
@patch("app.core.rag.cosine_similarity")
def test_recuperar_chunks_retorna_top_k_ordenados(mock_cos, mock_embed):
    """Los chunks deben ordenarse por score descendente y respetar top_k."""
    mock_embed.return_value = [[0.1, 0.2, 0.3]]
    mock_cos.side_effect = [0.9, 0.5, 0.7]  # scores no ordenados

    db = MagicMock()
    db.collection.return_value.where.return_value.stream.return_value = [
        _make_chunk_doc("A"),
        _make_chunk_doc("B"),
        _make_chunk_doc("C"),
    ]

    from app.core.rag import recuperar_chunks
    result = recuperar_chunks("curso1", "¿qué es X?", db, top_k=2, score_minimo=0.0)

    assert len(result) == 2
    assert result[0]["score"] >= result[1]["score"]
    assert result[0]["score"] == 0.9


@patch("app.core.rag.embed_texts")
def test_recuperar_chunks_sin_documentos(mock_embed):
    """Si no hay chunks, retorna lista vacía."""
    mock_embed.return_value = [[0.1, 0.2, 0.3]]

    db = MagicMock()
    db.collection.return_value.where.return_value.stream.return_value = []

    from app.core.rag import recuperar_chunks
    result = recuperar_chunks("curso1", "pregunta", db)

    assert result == []


@patch("app.core.rag.embed_texts")
@patch("app.core.rag.cosine_similarity")
def test_recuperar_chunks_filtra_score_minimo(mock_cos, mock_embed):
    """Chunks con score menor al mínimo no deben incluirse."""
    mock_embed.return_value = [[0.1, 0.2, 0.3]]
    mock_cos.side_effect = [0.1, 0.05, 0.8]  # 2 bajo el umbral de 0.3

    db = MagicMock()
    db.collection.return_value.where.return_value.stream.return_value = [
        _make_chunk_doc("A"),
        _make_chunk_doc("B"),
        _make_chunk_doc("C"),
    ]

    from app.core.rag import recuperar_chunks
    result = recuperar_chunks("curso1", "pregunta", db, top_k=5, score_minimo=0.3)

    assert len(result) == 1
    assert result[0]["score"] == 0.8


@patch("app.core.rag.embed_texts")
@patch("app.core.rag.cosine_similarity")
def test_recuperar_chunks_ignora_sin_embedding(mock_cos, mock_embed):
    """Chunks sin campo 'embedding' deben ignorarse."""
    mock_embed.return_value = [[0.1, 0.2, 0.3]]
    mock_cos.return_value = 0.9

    sin_embedding = MagicMock()
    sin_embedding.to_dict.return_value = {"curso_id": "c", "texto": "X", "pagina": 1}

    db = MagicMock()
    db.collection.return_value.where.return_value.stream.return_value = [sin_embedding]

    from app.core.rag import recuperar_chunks
    result = recuperar_chunks("curso1", "pregunta", db)

    assert result == []
    mock_cos.assert_not_called()
