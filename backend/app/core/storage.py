"""Cloud Storage: subida y eliminación de documentos (RF-08). Import lazy."""
from app.config import settings


def _get_bucket():
    from google.cloud import storage as gcs
    client = gcs.Client(project=settings.gcp_project_id)
    return client.bucket(settings.gcs_bucket_name)


def upload_file(file_bytes: bytes, destination: str, content_type: str) -> str:
    blob = _get_bucket().blob(destination)
    blob.upload_from_string(file_bytes, content_type=content_type)
    return f"gs://{settings.gcs_bucket_name}/{destination}"


def delete_file(gs_path: str) -> None:
    path = gs_path.replace(f"gs://{settings.gcs_bucket_name}/", "")
    blob = _get_bucket().blob(path)
    if blob.exists():
        blob.delete()
