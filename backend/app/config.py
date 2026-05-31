from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "ProfeTEC.IA"
    app_env: str = "development"
    app_version: str = "0.1.0"
    port: int = 8080
    cors_origins: str = "http://localhost:5174"
    allowed_email_domains: str = "tecsup.edu.pe"

    # Firebase
    firebase_project_id: Optional[str] = None
    google_application_credentials: Optional[str] = None

    # GCP / Vertex AI / Cloud Storage
    gcp_project_id: Optional[str] = None
    gcp_region: str = "us-central1"
    gcs_bucket_name: Optional[str] = None

    # RAG
    rag_top_k: int = 3
    rag_score_minimo: float = 0.3
    rag_score_confianza: float = 0.6
    rag_max_chunks_scan: int = 500
    rag_backend: str = "firestore_scan"

    # BigQuery Vector Search
    bigquery_dataset: str = "profetec_rag"
    bigquery_chunks_table: str = "chunks"
    bigquery_location: str = "US"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def allowed_email_domains_list(self) -> list[str]:
        return [d.strip().lower() for d in self.allowed_email_domains.split(",") if d.strip()]


settings = Settings()
