"""
Recuperación RAG — busca los chunks más relevantes para una pregunta (RF-13..RF-15).
Estrategia: embedding de la pregunta → similitud coseno contra todos los chunks del curso.
"""
from app.core.vertex import cosine_similarity, embed_texts


def recuperar_chunks(
    curso_id: str,
    pregunta: str,
    db,
    top_k: int = 5,
    score_minimo: float = 0.3,
) -> list[dict]:
    """
    1. Genera embedding de la pregunta.
    2. Lee todos los chunks del curso desde Firestore.
    3. Calcula similitud coseno con cada chunk.
    4. Retorna los top_k con score >= score_minimo, ordenados por relevancia.
    """
    # 1. Embedding de la pregunta
    [q_vec] = embed_texts([pregunta])

    # 2. Leer chunks del curso
    docs = (
        db.collection("chunks")
        .where("curso_id", "==", curso_id)
        .stream()
    )

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

    # 3. Ordenar por relevancia y retornar top_k
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_k]
