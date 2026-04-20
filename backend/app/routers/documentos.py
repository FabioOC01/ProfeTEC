"""
Gestión de conocimiento — upload, indexación y eliminación de documentos (RF-07..RF-12).
Pipeline: upload → extracción → chunking → embeddings → Firestore.
"""
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from firebase_admin import firestore

from app.core.auth import get_current_user
from app.core.chunker import chunk_pages
from app.core.extractor import DocType, extract_pages
from app.core.firestore_client import get_db
from app.core.storage import delete_file, upload_file
from app.core.vertex import embed_texts
from app.models.documento import DocumentoResponse

router = APIRouter(tags=["documentos"])

TIPOS_PERMITIDOS: dict[str, DocType] = {
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": "pptx",
    "text/plain": "txt",
}
MAX_SIZE_MB = 20


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


@router.post(
    "/cursos/{curso_id}/documentos",
    response_model=DocumentoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Subir y procesar documento (RF-08 a RF-11)",
)
async def subir_documento(
    curso_id: str,
    archivo: UploadFile = File(...),
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

    nombre = archivo.filename or "documento"

    # ── 1. Subir a Cloud Storage ──────────────────────────────────────────────
    storage_path = upload_file(
        file_bytes,
        destination=f"cursos/{curso_id}/{nombre}",
        content_type=content_type,
    )

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

    # ── 5. Guardar documento en Firestore ─────────────────────────────────────
    doc_data = {
        "curso_id": curso_id,
        "nombre": nombre,
        "tipo": doc_type,
        "storage_path": storage_path,
        "paginas": len(pages),
        "chunks_count": len(chunks),
        "docente_id": uid,
        "created_at": firestore.SERVER_TIMESTAMP,
    }
    _, doc_ref = db.collection("documentos").add(doc_data)
    doc_id = doc_ref.id

    # ── 6. Guardar chunks + embeddings en Firestore ───────────────────────────
    batch = db.batch()
    for chunk, vector in zip(chunks, vectores):
        chunk_ref = db.collection("chunks").document()
        batch.set(chunk_ref, {
            "documento_id": doc_id,
            "curso_id": curso_id,
            "nombre_doc": nombre,
            "texto": chunk["texto"],
            "embedding": vector,
            "pagina": chunk["pagina"],
            "posicion": chunk["posicion"],
        })
    batch.commit()

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
    # Cualquier usuario puede listar documentos (lectura); solo docentes pueden subir/eliminar
    doc = db.collection("cursos").document(curso_id).get()
    if not doc.exists:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Curso no encontrado.")

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

    doc_ref = db.collection("documentos").document(doc_id)
    doc = doc_ref.get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Documento no encontrado.")

    data = doc.to_dict()
    if data["docente_id"] != uid:
        raise HTTPException(status_code=403, detail="No tienes permiso para eliminar este documento.")

    # Eliminar chunks
    chunks = db.collection("chunks").where("documento_id", "==", doc_id).stream()
    batch = db.batch()
    for c in chunks:
        batch.delete(c.reference)
    batch.commit()

    # Eliminar archivo en Cloud Storage
    try:
        delete_file(data["storage_path"])
    except Exception:
        pass  # no bloquear si falla GCS

    doc_ref.delete()
