from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import health

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Tutor virtual con IA para estudiantes de TECSUP.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)


@app.get("/", tags=["root"])
def root() -> dict[str, str]:
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "env": settings.app_env,
        "docs": "/docs",
    }
