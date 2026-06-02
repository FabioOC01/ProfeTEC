"""Recuperacion RAG para preguntas del tutor (RF-13..RF-15)."""
import logging
import re

from app.config import settings
from app.core.vertex import cosine_similarity, embed_texts

logger = logging.getLogger(__name__)

_NUMEROS_SEMANA = {
    "uno": 1,
    "una": 1,
    "dos": 2,
    "tres": 3,
    "cuatro": 4,
    "cinco": 5,
    "seis": 6,
    "siete": 7,
    "ocho": 8,
    "nueve": 9,
    "diez": 10,
    "once": 11,
    "doce": 12,
    "trece": 13,
    "catorce": 14,
    "quince": 15,
    "dieciseis": 16,
    "dieciséis": 16,
    "diecisiete": 17,
    "dieciocho": 18,
    "diecinueve": 19,
    "veinte": 20,
    "veintiuno": 21,
    "veintiuna": 21,
    "veintidos": 22,
    "veintidós": 22,
    "veintitres": 23,
    "veintitrés": 23,
    "veinticuatro": 24,
    "veinticinco": 25,
    "veintiseis": 26,
    "veintiséis": 26,
    "veintisiete": 27,
    "veintiocho": 28,
    "veintinueve": 29,
    "treinta": 30,
}


def detectar_semana(texto: str) -> int | None:
    """Extrae una semana mencionada de forma explicita en la consulta.

    Soporta formas comunes: "semana 2", "semana dos", "sem. 2",
    "2da semana" y variantes con ordinal simple.
    """
    texto_norm = (texto or "").lower()
    patrones = [
        r"\bsem(?:ana|\.)?\s*(?:n[°ro.]*\s*)?(\d{1,2})\b",
        r"\b(\d{1,2})(?:ra|era|da|ta|a)?\s+semana\b",
    ]
    for patron in patrones:
        match = re.search(patron, texto_norm)
        if match:
            semana = int(match.group(1))
            if 1 <= semana <= 30:
                return semana

    match = re.search(
        r"\bsem(?:ana|\.)?\s*(?:n[°ro.]*\s*)?("
        + "|".join(sorted(_NUMEROS_SEMANA, key=len, reverse=True))
        + r")\b",
        texto_norm,
    )
    if match:
        return _NUMEROS_SEMANA[match.group(1)]
    return None


def _stream_chunks_firestore(curso_id: str, db, max_chunks_scan: int):
    query = db.collection("chunks").where("curso_id", "==", curso_id)
    if max_chunks_scan > 0:
        query = query.limit(max_chunks_scan)
    return query.stream()


def _rank_chunks(
    q_vec: list[float],
    docs,
    top_k: int,
    score_minimo: float,
    semana: int | None = None,
) -> list[dict]:
    scored = []
    for doc in docs:
        data = doc.to_dict()
        if semana is not None:
            try:
                if int(data.get("semana")) != semana:
                    continue
            except (TypeError, ValueError):
                continue

        vec = data.get("embedding")
        if not vec:
            continue

        score = cosine_similarity(q_vec, vec)
        # Si el usuario pide una semana exacta, el metadato es una señal fuerte.
        # No dependemos solo de la similitud del texto "repasar semana 2", que es
        # demasiado genérico para un embedding.
        if semana is not None or score >= score_minimo:
            scored.append({
                "score": max(score, settings.rag_score_confianza)
                if semana is not None
                else score,
                "documento_id": data.get("documento_id", ""),
                "nombre_doc": data.get("nombre_doc", ""),
                "texto": data.get("texto", ""),
                "pagina": data.get("pagina", 1),
                "semana": data.get("semana"),
                "metadata_match": semana is not None,
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
    ignorar_semana: bool = False,
) -> list[dict]:
    """
    Genera el embedding de la pregunta y retorna los chunks mas relevantes.

    Backend actual: `firestore_scan` o `bigquery_vector`, con fallback a Firestore
    si BigQuery no esta disponible para no romper la demo.

    `ignorar_semana=True` desactiva el filtro por semana aunque la pregunta la
    mencione: busca por similitud en todo el curso. Se usa para sugerir el
    material mas parecido cuando la semana pedida no tiene contenido indexado.
    """
    resolved_top_k = top_k if top_k is not None else settings.rag_top_k
    resolved_score_minimo = (
        score_minimo if score_minimo is not None else settings.rag_score_minimo
    )
    resolved_max_chunks_scan = (
        max_chunks_scan if max_chunks_scan is not None else settings.rag_max_chunks_scan
    )
    semana = None if ignorar_semana else detectar_semana(pregunta)
    if semana is not None and top_k is None:
        resolved_top_k = max(resolved_top_k, 5)

    [q_vec] = embed_texts([pregunta])

    if settings.rag_backend == "bigquery_vector":
        try:
            from app.core.bigquery_rag import search_chunks

            results = search_chunks(
                curso_id,
                q_vec,
                resolved_top_k,
                -1.0 if semana is not None else resolved_score_minimo,
                semana=semana,
            )
            if results:
                if semana is not None:
                    for result in results:
                        result["score"] = max(
                            result.get("score", 0.0),
                            settings.rag_score_confianza,
                        )
                        result["metadata_match"] = True
                return results
            if semana is None:
                return results
            logger.info(
                "BigQuery no devolvio chunks para semana=%s; probando Firestore scan.",
                semana,
            )
        except Exception as exc:
            logger.warning(
                "BigQuery Vector Search fallo; usando Firestore scan. error=%s",
                exc,
            )
    elif settings.rag_backend != "firestore_scan":
        raise ValueError(f"RAG backend no soportado: {settings.rag_backend}")

    docs = _stream_chunks_firestore(curso_id, db, resolved_max_chunks_scan)
    return _rank_chunks(q_vec, docs, resolved_top_k, resolved_score_minimo, semana)
