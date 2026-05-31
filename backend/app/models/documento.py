from typing import Literal, Optional
from pydantic import BaseModel, Field

TipoDoc = Literal["pdf", "pptx", "txt"]


class DocumentoResponse(BaseModel):
    id: str
    curso_id: str
    nombre: str
    tipo: TipoDoc
    storage_path: str
    paginas: int
    chunks_count: int
    docente_id: str
    semana: Optional[int] = Field(default=None, ge=1, le=30)
    referencia: Optional[str] = Field(default=None, max_length=300)
