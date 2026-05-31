"""Recuperacion RAG para preguntas del tutor (RF-13..RF-15)."""
import logging

from app.config import settings
from app.core.vertex import cosine_similarity, embed_texts

logger = logging.getLogger(__name__)


def _stream_chunks_firestore(curso_id: str, db, max_chunks_scan: int):
    query = db.collection("chunks").where("curso_id", "==", curso_id)
    if max_chunks_scan > 0:
        query = query.limit(max_chunks_scan)
    return query.stream()


def _rank_chunks(q_vec: list[float], docs, top_k: int, score_minimo: float) -> list[dict]:
    scored = []
    for doc in docs:
        data = doc.to_dict()
        vec = data.get("embedding")
        if not vec:
            continue

        score = cosine_similarity(q_vec, vec)
        if score >= score_minimo:
            scored.append({
                "score": score,
                "documento_id": data.get("documento_id", ""),
                "nombre_doc": data.get("nombre_doc", ""),
                "texto": data.get("texto", ""),
                "pagina": data.get("pagina", 1),
            })

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_k]


def recuperar_chunks(
    curso_id: str,
    pregunta: str,
    db,
    top_k: int | None = None,
    score_minimo: float | None = None,
    max_chunks_scan: int | None = None,
) -> list[dict]:
    """
    Genera el embedding de la pregunta y retorna los chunks mas relevantes.

    Backend actual: `firestore_scan` o `bigquery_vector`, con fallback a Firestore
    si BigQuery no esta disponible para no romper la demo.
    """
    resolved_top_k = top_k if top_k is not None else settings.rag_top_k
    resolved_score_minimo = (
        score_minimo if score_minimo is not None else settings.rag_score_minimo
    )
    resolved_max_chunks_scan = (
        max_chunks_scan if max_chunks_scan is not None else settings.rag_max_chunks_scan
    )

    [q_vec] = embed_texts([pregunta])

    if settings.rag_backend == "bigquery_vector":
        try:
            from app.core.bigquery_rag import search_chunks

            return search_chunks(
                curso_id,
                q_vec,
                resolved_top_k,
                resolved_score_minimo,
            )
        except Exception as exc:
            logger.warning(
                "BigQuery Vector Search fallo; usando Firestore scan. error=%s",
                exc,
            )
    elif settings.rag_backend != "firestore_scan":
        raise ValueError(f"RAG backend no soportado: {settings.rag_backend}")

    docs = _stream_chunks_firestore(curso_id, db, resolved_max_chunks_scan)
    return _rank_chunks(q_vec, docs, resolved_top_k, resolved_score_minimo)
