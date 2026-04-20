from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.core.firebase import init_firebase
from app.routers import health
from app.routers import auth_router, cursos, documentos, chat

# Intentar inicializar Firebase al arrancar (falla silenciosamente si no hay credenciales)
init_firebase()

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
app.include_router(auth_router.router)
app.include_router(cursos.router)
app.include_router(documentos.router)
app.include_router(chat.router)


@app.get("/", tags=["root"])
def root() -> dict[str, str]:
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "env": settings.app_env,
        "docs": "/docs",
    }
