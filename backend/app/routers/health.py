from datetime import datetime, timezone

from fastapi import APIRouter
from pydantic import BaseModel

from app.config import settings

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str
    app: str
    version: str
    env: str
    timestamp: str


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        app=settings.app_name,
        version=settings.app_version,
        env=settings.app_env,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
