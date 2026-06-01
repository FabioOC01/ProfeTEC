"""
Gestión de conocimiento — upload, indexación y eliminación de documentos (RF-07..RF-12).
Pipeline: upload → extracción → chunking → embeddings → Firestore.
"""
import logging
from pathlib import PurePath
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from firebase_admin import firestore

from app.core.access import verificar_acceso_curso
from app.core.auth import get_current_user
from app.core.chunker import chunk_pages
from app.core.extractor import DocType, extract_pages
from app.core.firestore_client import get_db
from app.core.storage import delete_file, upload_file
from app.core.vertex import embed_texts
from app.models.documento import CoberturaDocumentosResponse, DocumentoResponse

router = APIRouter(tags=["documentos"])
logger = logging.getLogger(__name__)

TIPOS_PERMITIDOS: dict[str, DocType] = {
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": "pptx",
    "text/plain": "txt",
}
EXTENSIONES_PERMITIDAS: dict[DocType, set[str]] = {
    "pdf": {".pdf"},
    "pptx": {".pptx"},
    "txt": {".txt"},
}
MAX_SIZE_MB = 20
FIRESTORE_BATCH_LIMIT = 450


def _verificar_docente(uid: str, db) -> dict:
    doc = db.collection("usuarios").document(uid).get()
    if not doc.exists or doc.to_dict().get("rol") != "docente":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Solo los docentes pueden gestionar documentos.")
    return doc.to_dict()


def _verificar_curso(curso_id: str, uid: str, db) -> dict:
    doc = db.collection("cursos").document(curso_id).get()
    if not doc.exists:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Curso no encontrado.")
    data = doc.to_dict()
    if data["docente_id"] != uid:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="No tienes acceso a este curso.")
    return data


def _nombre_seguro(filename: str | None) -> str:
    nombre = PurePath(filename or "documento").name.strip() or "documento"
    return nombre.replace("/", "_").replace("\\", "_")


def _texto_seguro(value: str | None) -> str:
    return (value or "").strip().replace("/", "_").replace("\\", "_")


def _validar_extension(nombre: str, doc_type: DocType) -> None:
    extension = PurePath(nombre).suffix.lower()
    if extension not in EXTENSIONES_PERMITIDAS[doc_type]:
        permitidas = ", ".join(sorted(EXTENSIONES_PERMITIDAS[doc_type]))
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"La extension del archivo no coincide con el tipo. Usa: {permitidas}.",
        )


def _storage_destination(curso_id: str, nombre: str) -> str:
    return f"cursos/{curso_id}/{uuid4().hex}_{nombre}"


def _commit_chunks_en_batches(
    db,
    chunks: list[dict],
    vectores: list[list[float]],
    doc_id: str,
    curso_id: str,
    nombre: str,
    semana: int | None = None,
    referencia: str | None = None,
) -> list[str]:
    batch = db.batch()
    operaciones = 0
    chunk_ids: list[str] = []

    for chunk, vector in zip(chunks, vectores):
        chunk_ref = db.collection("chunks").document()
        chunk_ids.append(chunk_ref.id)
        batch.set(chunk_ref, {
            "documento_id": doc_id,
            "curso_id": curso_id,
            "nombre_doc": nombre,
            "texto": chunk["texto"],
            "embedding": vector,
            "pagina": chunk["pagina"],
            "posicion": chunk["posicion"],
            "semana": semana,
            "referencia": referencia,
        })
        operaciones += 1

        if operaciones >= FIRESTORE_BATCH_LIMIT:
            batch.commit()
            batch = db.batch()
            operaciones = 0

    if operaciones:
        batch.commit()

    return chunk_ids


def _insert_chunks_bigquery_best_effort(
    chunks: list[dict],
    vectores: list[list[float]],
    chunk_ids: list[str],
    doc_id: str,
    curso_id: str,
    nombre: str,
    semana: int | None = None,
    referencia: str | None = None,
) -> None:
    try:
        from app.core.bigquery_rag import build_chunk_rows, insert_chunk_rows

        rows = build_chunk_rows(
            chunks,
            vectores,
            chunk_ids,
            doc_id,
            curso_id,
            nombre,
            semana,
            referencia,
        )
        insert_chunk_rows(rows)
    except Exception as exc:
        logger.warning("No se pudieron indexar chunks en BigQuery: %s", exc)


def _delete_chunks_en_batches(db, doc_id: str) -> None:
    chunks = db.collection("chunks").where("documento_id", "==", doc_id).stream()
    batch = db.batch()
    operaciones = 0

    for chunk in chunks:
        batch.delete(chunk.reference)
        operaciones += 1

        if operaciones >= FIRESTORE_BATCH_LIMIT:
            batch.commit()
            batch = db.batch()
            operaciones = 0

    if operaciones:
        batch.commit()


def _delete_chunks_bigquery_best_effort(doc_id: str) -> None:
    try:
        from app.core.bigquery_rag import delete_chunks_for_document

        delete_chunks_for_document(doc_id)
    except Exception as exc:
        logger.warning("No se pudieron eliminar chunks en BigQuery: %s", exc)


@router.post(
    "/cursos/{curso_id}/documentos",
    response_model=DocumentoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Subir y procesar documento (RF-08 a RF-11)",
)
async def subir_documento(
    curso_id: str,
    archivo: UploadFile = File(...),
    titulo: str = Form(..., min_length=1, max_length=160),
    semana: int = Form(..., ge=1, le=30),
    referencia: str | None = Form(default=None, max_length=300),
    claims: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """
    Pipeline completo de ingesta:
    1. Valida tipo y tamaño (PDF / PPTx / TXT, máx 20 MB).
    2. Sube el archivo a Cloud Storage.
    3. Extrae texto con metadatos de página/diapositiva.
    4. Fragmenta en chunks con solapamiento.
    5. Genera embeddings vía Vertex AI (text-embedding-004).
    6. Persiste chunks + embeddings en Firestore.
    """
    uid = claims["uid"]
    _verificar_docente(uid, db)
    _verificar_curso(curso_id, uid, db)

    # ── Validar tipo ──────────────────────────────────────────────────────────
    content_type = archivo.content_type or ""
    doc_type = TIPOS_PERMITIDOS.get(content_type)
    if doc_type is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Tipo no soportado: {content_type}. Usa PDF, PPTx o TXT.",
        )

    # ── Leer y validar tamaño ─────────────────────────────────────────────────
    file_bytes = await archivo.read()
    if len(file_bytes) > MAX_SIZE_MB * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"El archivo supera el límite de {MAX_SIZE_MB} MB.",
        )

    nombre_archivo = _nombre_seguro(archivo.filename)
    nombre_doc = _texto_seguro(titulo)
    referencia_doc = _texto_seguro(referencia) or None
    if not nombre_doc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="El titulo del documento es obligatorio.",
        )
    _validar_extension(nombre_archivo, doc_type)

    # ── 1. Subir a Cloud Storage ──────────────────────────────────────────────
    # ── 2. Extraer texto ──────────────────────────────────────────────────────
    pages = extract_pages(file_bytes, doc_type)
    if not pages:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No se pudo extraer texto del documento.",
        )

    # ── 3. Chunking ───────────────────────────────────────────────────────────
    chunks = chunk_pages(pages)

    # ── 4. Embeddings (Vertex AI) ─────────────────────────────────────────────
    textos = [c["texto"] for c in chunks]
    vectores = embed_texts(textos)
    if len(vectores) != len(chunks):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="No se generaron embeddings para todos los chunks.",
        )

    storage_path = upload_file(
        file_bytes,
        destination=_storage_destination(curso_id, nombre_archivo),
        content_type=content_type,
    )

    # ── 5. Guardar documento en Firestore ─────────────────────────────────────
    doc_data = {
        "curso_id": curso_id,
        "nombre": nombre_doc,
        "tipo": doc_type,
        "storage_path": storage_path,
        "paginas": len(pages),
        "chunks_count": len(chunks),
        "docente_id": uid,
        "semana": semana,
        "referencia": referencia_doc,
        "created_at": firestore.SERVER_TIMESTAMP,
    }
    doc_ref = None
    doc_id = None
    try:
        _, doc_ref = db.collection("documentos").add(doc_data)
        doc_id = doc_ref.id
        chunk_ids = _commit_chunks_en_batches(
            db,
            chunks,
            vectores,
            doc_id,
            curso_id,
            nombre_doc,
            semana,
            referencia_doc,
        )
        _insert_chunks_bigquery_best_effort(
            chunks,
            vectores,
            chunk_ids,
            doc_id,
            curso_id,
            nombre_doc,
            semana,
            referencia_doc,
        )
    except Exception:
        if doc_id:
            try:
                _delete_chunks_en_batches(db, doc_id)
                doc_ref.delete()
            except Exception:
                pass
        try:
            delete_file(storage_path)
        except Exception:
            pass
        raise

    # ── 6. Guardar chunks + embeddings en Firestore ───────────────────────────
    return {**doc_data, "id": doc_id}


@router.get(
    "/cursos/{curso_id}/documentos",
    response_model=list[DocumentoResponse],
    summary="Listar documentos de un curso (RF-12)",
)
def listar_documentos(
    curso_id: str,
    claims: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    uid = claims["uid"]
    verificar_acceso_curso(curso_id, uid, db)

    docs = (
        db.collection("documentos")
        .where("curso_id", "==", curso_id)
        .stream()
    )
    result = []
    for d in docs:
        data = d.to_dict()
        data["id"] = d.id
        data.pop("created_at", None)
        result.append(data)
    return result


@router.get(
    "/cursos/{curso_id}/documentos/cobertura",
    response_model=CoberturaDocumentosResponse,
    summary="Cobertura de documentos por semana",
)
def cobertura_documentos(
    curso_id: str,
    claims: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    uid = claims["uid"]
    verificar_acceso_curso(curso_id, uid, db)

    docs = (
        db.collection("documentos")
        .where("curso_id", "==", curso_id)
        .stream()
    )
    por_semana: dict[int, dict] = {}
    total_documentos = 0
    total_chunks = 0

    for d in docs:
        data = d.to_dict() or {}
        total_documentos += 1
        chunks = int(data.get("chunks_count") or 0)
        paginas = int(data.get("paginas") or 0)
        total_chunks += chunks
        try:
            semana = int(data.get("semana"))
        except (TypeError, ValueError):
            continue
        if not 1 <= semana <= 30:
            continue
        item = por_semana.setdefault(
            semana,
            {"semana": semana, "documentos": 0, "chunks": 0, "paginas": 0, "nombres": []},
        )
        item["documentos"] += 1
        item["chunks"] += chunks
        item["paginas"] += paginas
        nombre = data.get("nombre")
        if nombre:
            item["nombres"].append(nombre)

    semanas = [por_semana[k] for k in sorted(por_semana)]
    semanas_sin_chunks = [
        item["semana"]
        for item in semanas
        if item["chunks"] <= 0
    ]

    return {
        "curso_id": curso_id,
        "total_documentos": total_documentos,
        "total_chunks": total_chunks,
        "semanas": semanas,
        "semanas_sin_chunks": semanas_sin_chunks,
    }


@router.delete(
    "/cursos/{curso_id}/documentos/{doc_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar documento y sus chunks (RF-12)",
)
def eliminar_documento(
    curso_id: str,
    doc_id: str,
    claims: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    uid = claims["uid"]
    _verificar_docente(uid, db)
    _verificar_curso(curso_id, uid, db)

    doc_ref = db.collection("documentos").document(doc_id)
    doc = doc_ref.get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Documento no encontrado.")

    data = doc.to_dict()
    if data.get("curso_id") != curso_id:
        raise HTTPException(status_code=404, detail="Documento no encontrado en este curso.")

    if data["docente_id"] != uid:
        raise HTTPException(status_code=403, detail="No tienes permiso para eliminar este documento.")

    _delete_chunks_en_batches(db, doc_id)
    _delete_chunks_bigquery_best_effort(doc_id)

    # Eliminar archivo en Cloud Storage
    try:
        delete_file(data["storage_path"])
    except Exception:
        pass  # no bloquear si falla GCS

    doc_ref.delete()
