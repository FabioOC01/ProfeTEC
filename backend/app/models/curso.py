from typing import Optional
from pydantic import BaseModel, field_validator


class CursoCreate(BaseModel):
    nombre: str
    descripcion: Optional[str] = None

    @field_validator("nombre")
    @classmethod
    def nombre_no_vacio(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("El nombre del curso no puede estar vacío.")
        return v.strip()


class CursoUpdate(BaseModel):
    nombre: Optional[str] = None
    descripcion: Optional[str] = None
    activo: Optional[bool] = None


class CursoResponse(BaseModel):
    id: str
    nombre: str
    descripcion: Optional[str] = None
    docente_id: str
    docente_nombre: str
    codigo: str
    activo: bool
