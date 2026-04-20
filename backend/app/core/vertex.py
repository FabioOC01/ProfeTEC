"""
Generación de embeddings vía Vertex AI (RF-11).
Modelo: text-embedding-004 (768 dimensiones).
Import lazy para que los tests corran sin google-cloud-aiplatform instalado.
Usa credenciales explícitas del service account para evitar conflictos con ADC.
"""
import math
import os
from typing import TYPE_CHECKING

from app.config import settings

if TYPE_CHECKING:
    pass

_client = None


def _get_client():
    """Devuelve un EmbeddingModel usando la nueva API de Vertex AI."""
    global _client
    if _client is None:
        import vertexai
        from vertexai.language_models import TextEmbeddingModel

        project = settings.gcp_project_id or settings.firebase_project_id
        location = settings.gcp_region

        # Intentar cargar credenciales explícitas del service account
        cred_path = settings.google_application_credentials or os.environ.get(
            "GOOGLE_APPLICATION_CREDENTIALS"
        )
        credentials = None
        if cred_path and os.path.exists(cred_path):
            from google.oauth2 import service_account
            credentials = service_account.Credentials.from_service_account_file(
                cred_path,
                scopes=["https://www.googleapis.com/auth/cloud-platform"],
            )

        vertexai.init(project=project, location=location, credentials=credentials)
        _client = TextEmbeddingModel.from_pretrained("text-embedding-004")
    return _client


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Genera embeddings para una lista de textos. Retorna lista de vectores."""
    model = _get_client()
    results = []
    for i in range(0, len(texts), 50):
        batch = texts[i: i + 50]
        embeddings = model.get_embeddings(batch)
        results.extend([e.values for e in embeddings])
    return results


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Similitud coseno entre dos vectores."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    return dot / (norm_a * norm_b) if norm_a and norm_b else 0.0
