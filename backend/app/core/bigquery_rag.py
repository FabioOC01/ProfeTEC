"""BigQuery Vector Search helpers for the RAG index."""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.config import settings

logger = logging.getLogger(__name__)

VECTOR_INDEX_NAME = "idx_chunks_embedding"


def _get_client():
    from google.cloud import bigquery

    project = settings.gcp_project_id or settings.firebase_project_id
    return bigquery.Client(project=project, location=settings.bigquery_location)


def _table_id(client=None) -> str:
    active_client = client or _get_client()
    project = settings.gcp_project_id or settings.firebase_project_id or active_client.project
    return f"{project}.{settings.bigquery_dataset}.{settings.bigquery_chunks_table}"


def create_table_sql() -> str:
    table = _table_id()
    return f"""
CREATE TABLE IF NOT EXISTS `{table}` (
  chunk_id STRING NOT NULL,
  curso_id STRING NOT NULL,
  documento_id STRING NOT NULL,
  nombre_doc STRING,
  texto STRING,
  pagina INT64,
  posicion INT64,
  semana INT64,
  referencia STRING,
  embedding ARRAY<FLOAT64>,
  created_at TIMESTAMP
)
CLUSTER BY curso_id, documento_id
""".strip()


def create_vector_index_sql() -> str:
    table = _table_id()
    # STORING (curso_id, semana) permite que el pre-filtro de search_chunks
    # use el indice IVF en lugar de caer a fuerza bruta sobre toda la tabla.
    # (Requiere >= 5000 filas para que BigQuery construya/use el indice.)
    return f"""
CREATE VECTOR INDEX IF NOT EXISTS {VECTOR_INDEX_NAME}
ON `{table}`(embedding)
STORING (curso_id, semana)
OPTIONS(distance_type = 'COSINE', index_type = 'IVF')
""".strip()


def drop_vector_index_sql() -> str:
    table = _table_id()
    return f"DROP VECTOR INDEX IF EXISTS {VECTOR_INDEX_NAME} ON `{table}`"


def ensure_dataset(client=None) -> None:
    """Crea el dataset en la location configurada si aun no existe."""
    from google.cloud import bigquery

    active_client = client or _get_client()
    project = (
        settings.gcp_project_id
        or settings.firebase_project_id
        or active_client.project
    )
    dataset = bigquery.Dataset(f"{project}.{settings.bigquery_dataset}")
    dataset.location = settings.bigquery_location
    active_client.create_dataset(dataset, exists_ok=True)


def ensure_schema(recreate_index: bool = False) -> None:
    """Crea dataset + tabla + indice vectorial de forma idempotente.

    `recreate_index=True` dropea el indice existente antes de recrearlo; usalo
    una vez para migrar un indice antiguo creado sin `STORING (curso_id, semana)`,
    ya que `CREATE VECTOR INDEX IF NOT EXISTS` no recrea uno que ya existe.
    """
    client = _get_client()
    ensure_dataset(client)
    client.query(create_table_sql()).result()
    if recreate_index:
        logger.info("Dropeando indice vectorial existente para recrearlo.")
        client.query(drop_vector_index_sql()).result()
    try:
        client.query(create_vector_index_sql()).result()
        logger.info("Esquema BigQuery del RAG listo (dataset, tabla, indice).")
    except Exception as exc:
        # BigQuery exige >= 5000 filas para crear un indice IVF. Con menos,
        # VECTOR_SEARCH funciona igual (fuerza bruta); no es un fallo fatal.
        if "min allowed 5000" in str(exc):
            logger.warning(
                "Indice vectorial no creado: la tabla tiene <5000 filas. "
                "VECTOR_SEARCH seguira funcionando por fuerza bruta. "
                "Re-ejecuta este script cuando la tabla crezca."
            )
        else:
            raise


def build_chunk_rows(
    chunks: list[dict],
    vectores: list[list[float]],
    chunk_ids: list[str],
    doc_id: str,
    curso_id: str,
    nombre: str,
    semana: int | None = None,
    referencia: str | None = None,
) -> list[dict]:
    now = datetime.now(timezone.utc).isoformat()
    rows = []
    for chunk, vector, chunk_id in zip(chunks, vectores, chunk_ids):
        rows.append({
            "chunk_id": chunk_id,
            "curso_id": curso_id,
            "documento_id": doc_id,
            "nombre_doc": nombre,
            "texto": chunk["texto"],
            "pagina": int(chunk["pagina"]),
            "posicion": int(chunk["posicion"]),
            "semana": semana,
            "referencia": referencia,
            "embedding": [float(v) for v in vector],
            "created_at": now,
        })
    return rows


def insert_chunk_rows(rows: list[dict]) -> None:
    if not rows:
        return
    from google.cloud import bigquery

    # Usamos un load job (no streaming insert): es gratis, las filas quedan
    # disponibles en almacenamiento de inmediato y se pueden borrar al instante.
    # El streaming buffer bloquea DELETE ~30-90 min, lo que rompia el reemplazo
    # de documentos (delete_chunks_for_document) dejando chunks duplicados.
    client = _get_client()
    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
    )
    job = client.load_table_from_json(rows, _table_id(client), job_config=job_config)
    job.result()
    if job.errors:
        raise RuntimeError(f"BigQuery load job returned errors: {job.errors}")


def delete_chunks_for_document(doc_id: str) -> None:
    from google.cloud import bigquery

    client = _get_client()
    query = f"DELETE FROM `{_table_id(client)}` WHERE documento_id = @doc_id"
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("doc_id", "STRING", doc_id),
        ]
    )
    client.query(query, job_config=job_config).result()


def search_chunks(
    curso_id: str,
    query_embedding: list[float],
    top_k: int,
    score_minimo: float,
    semana: int | None = None,
) -> list[dict]:
    """Return chunks ranked by BigQuery VECTOR_SEARCH."""
    from google.cloud import bigquery

    client = _get_client()
    table = _table_id(client)
    filtro_semana = "AND semana = @semana" if semana is not None else ""
    query = f"""
SELECT
  base.chunk_id,
  base.documento_id,
  base.nombre_doc,
  base.texto,
  base.pagina,
  base.semana,
  distance
FROM VECTOR_SEARCH(
  (SELECT * FROM `{table}` WHERE curso_id = @curso_id {filtro_semana}),
  'embedding',
  (SELECT @query_embedding AS embedding),
  top_k => @top_k,
  distance_type => 'COSINE'
)
WHERE (1 - distance) >= @score_minimo
ORDER BY distance ASC
""".strip()
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("curso_id", "STRING", curso_id),
            *(
                [bigquery.ScalarQueryParameter("semana", "INT64", semana)]
                if semana is not None
                else []
            ),
            bigquery.ArrayQueryParameter(
                "query_embedding",
                "FLOAT64",
                [float(v) for v in query_embedding],
            ),
            bigquery.ScalarQueryParameter("top_k", "INT64", top_k),
            bigquery.ScalarQueryParameter("score_minimo", "FLOAT64", score_minimo),
        ]
    )
    rows = client.query(query, job_config=job_config).result()
    return [
        {
            "score": 1 - float(row.distance),
            "documento_id": row.documento_id,
            "nombre_doc": row.nombre_doc or "",
            "texto": row.texto or "",
            "pagina": row.pagina or 1,
            "semana": row.semana,
        }
        for row in rows
    ]
