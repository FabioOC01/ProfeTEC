"""Tests del extractor y chunker — sin dependencias de red (RF-09, RF-10)."""
from app.core.chunker import chunk_pages
from app.core.extractor import _extract_txt


class TestExtractorTxt:
    def test_extrae_texto_simple(self):
        texto = "Hola mundo. Este es un documento de prueba."
        pages = _extract_txt(texto.encode("utf-8"))
        assert len(pages) == 1
        assert pages[0][0] == 1  # página 1
        assert "Hola mundo" in pages[0][1]

    def test_texto_vacio_retorna_lista_vacia(self):
        pages = _extract_txt(b"   ")
        assert pages == []

    def test_caracteres_especiales(self):
        texto = "Inteligencia Artificial: IA, ML, DL — conceptos clave."
        pages = _extract_txt(texto.encode("utf-8"))
        assert len(pages) == 1


class TestChunker:
    def test_texto_corto_produce_un_chunk(self):
        pages = [(1, "Texto corto de prueba.")]
        chunks = chunk_pages(pages, chunk_size=800, overlap=150)
        assert len(chunks) == 1
        assert chunks[0]["pagina"] == 1
        assert chunks[0]["posicion"] == 0

    def test_texto_largo_produce_multiples_chunks(self):
        texto_largo = "A" * 2500
        pages = [(1, texto_largo)]
        chunks = chunk_pages(pages, chunk_size=800, overlap=150)
        assert len(chunks) >= 3

    def test_chunks_conservan_numero_de_pagina(self):
        pages = [(1, "Página uno " * 50), (2, "Página dos " * 50)]
        chunks = chunk_pages(pages, chunk_size=200, overlap=50)
        paginas = {c["pagina"] for c in chunks}
        assert 1 in paginas
        assert 2 in paginas

    def test_posicion_es_incremental(self):
        pages = [(1, "X" * 3000)]
        chunks = chunk_pages(pages, chunk_size=800, overlap=150)
        posiciones = [c["posicion"] for c in chunks]
        assert posiciones == list(range(len(chunks)))

    def test_paginas_vacias_se_omiten(self):
        pages = [(1, "   "), (2, "Contenido real.")]
        chunks = chunk_pages(pages)
        assert all(c["pagina"] == 2 for c in chunks)
