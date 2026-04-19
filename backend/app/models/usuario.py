from typing import Literal, Optional
from pydantic import BaseModel

Rol = Literal["docente", "estudiante"]


class UsuarioResponse(BaseModel):
    uid: str
    email: str
    nombre: str
    foto_url: Optional[str] = None
    rol: Optional[Rol] = None


class SetRolRequest(BaseModel):
    rol: Rol
