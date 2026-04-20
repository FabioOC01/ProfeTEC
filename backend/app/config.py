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

    # Firebase
    firebase_project_id: Optional[str] = None
    google_application_credentials: Optional[str] = None

    # GCP / Vertex AI / Cloud Storage
    gcp_project_id: Optional[str] = None
    gcp_region: str = "us-central1"
    gcs_bucket_name: Optional[str] = None

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
