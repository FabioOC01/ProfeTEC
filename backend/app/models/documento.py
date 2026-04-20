from typing import Literal, Optional
from pydantic import BaseModel

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
