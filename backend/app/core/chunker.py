"""
Fragmentación (chunking) de texto para indexación RAG (RF-10).
Cada chunk conserva el número de página/diapositiva de origen para citas (RF-16).
"""


def chunk_pages(
    pages: list[tuple[int, str]],
    chunk_size: int = 800,
    overlap: int = 150,
) -> list[dict]:
    """
    Divide el texto de cada página en chunks de tamaño fijo con solapamiento.

    Args:
        pages:      Lista de (numero_pagina, texto).
        chunk_size: Tamaño máximo de cada chunk en caracteres.
        overlap:    Cantidad de caracteres que se repiten entre chunks consecutivos.

    Returns:
        Lista de dicts con keys: texto, pagina, posicion.
    """
    chunks: list[dict] = []
    posicion = 0

    for pagina, texto in pages:
        start = 0
        while start < len(texto):
            end = start + chunk_size
            fragmento = texto[start:end].strip()
            if fragmento:
                chunks.append(
                    {"texto": fragmento, "pagina": pagina, "posicion": posicion}
                )
                posicion += 1
            start += chunk_size - overlap

    return chunks
