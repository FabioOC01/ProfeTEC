"""Tests del backend BigQuery del RAG: ingesta (load job) e indice vectorial."""
from unittest.mock import MagicMock, patch


@patch("app.core.bigquery_rag._get_client")
def test_create_vector_index_usa_storing_para_prefiltro(mock_client):
    """El indice debe almacenar curso_id/semana para que el pre-filtro use IVF
    en vez de fuerza bruta sobre toda la tabla."""
    mock_client.return_value = MagicMock(project="proj-test")

    from app.core.bigquery_rag import create_vector_index_sql

    sql = create_vector_index_sql()
    assert "STORING (curso_id, semana)" in sql
    assert "index_type = 'IVF'" in sql


@patch("app.core.bigquery_rag._get_client")
def test_insert_chunk_rows_usa_load_job_no_streaming(mock_get_client):
    """insert_chunk_rows debe usar load_table_from_json (load job), no
    insert_rows_json (streaming), para permitir borrados inmediatos."""
    client = MagicMock(project="proj-test")
    job = MagicMock()
    job.errors = None
    client.load_table_from_json.return_value = job
    mock_get_client.return_value = client

    from app.core.bigquery_rag import insert_chunk_rows

    rows = [{"chunk_id": "c1", "curso_id": "curso1", "documento_id": "doc1"}]
    insert_chunk_rows(rows)

    client.load_table_from_json.assert_called_once()
    client.insert_rows_json.assert_not_called()
    job.result.assert_called_once()
    args, _ = client.load_table_from_json.call_args
    assert args[0] == rows


@patch("app.core.bigquery_rag._get_client")
def test_insert_chunk_rows_propaga_errores_del_job(mock_get_client):
    client = MagicMock(project="proj-test")
    job = MagicMock()
    job.errors = [{"reason": "invalid"}]
    client.load_table_from_json.return_value = job
    mock_get_client.return_value = client

    from app.core.bigquery_rag import insert_chunk_rows

    import pytest

    with pytest.raises(RuntimeError):
        insert_chunk_rows([{"chunk_id": "c1", "curso_id": "c", "documento_id": "d"}])


def test_insert_chunk_rows_vacio_no_llama_cliente():
    from app.core.bigquery_rag import insert_chunk_rows

    with patch("app.core.bigquery_rag._get_client") as mock_get_client:
        insert_chunk_rows([])
        mock_get_client.assert_not_called()


@patch("app.core.bigquery_rag._get_client")
def test_ensure_schema_crea_tabla_e_indice_idempotente(mock_get_client):
    client = MagicMock(project="proj-test")
    mock_get_client.return_value = client

    from app.core.bigquery_rag import ensure_schema

    ensure_schema()

    queries = [call.args[0] for call in client.query.call_args_list]
    assert any("CREATE TABLE IF NOT EXISTS" in q for q in queries)
    assert any("CREATE VECTOR INDEX IF NOT EXISTS" in q for q in queries)
    assert not any("DROP VECTOR INDEX" in q for q in queries)
    client.create_dataset.assert_called_once()


@patch("app.core.bigquery_rag._get_client")
def test_ensure_schema_recreate_index_dropea_antes_de_crear(mock_get_client):
    client = MagicMock(project="proj-test")
    mock_get_client.return_value = client

    from app.core.bigquery_rag import ensure_schema

    ensure_schema(recreate_index=True)

    queries = [call.args[0] for call in client.query.call_args_list]
    drop_idx = next(i for i, q in enumerate(queries) if "DROP VECTOR INDEX IF EXISTS" in q)
    create_idx = next(i for i, q in enumerate(queries) if "CREATE VECTOR INDEX" in q)
    assert drop_idx < create_idx
