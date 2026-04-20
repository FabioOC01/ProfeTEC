from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    pregunta: str = Field(..., min_length=1, max_length=2000)
    conversacion_id: Optional[str] = None


class ChunkCitado(BaseModel):
    documento_id: str
    nombre_doc: str
    pagina: int
    fragmento: str  # primeros 200 chars del chunk


class ChatResponse(BaseModel):
    respuesta: str
    conversacion_id: str
    mensaje_id: str
    chunks_usados: list[ChunkCitado]
    creado_en: datetime


class MensajeOut(BaseModel):
    id: str
    pregunta: str
    respuesta: str
    chunks_usados: list[ChunkCitado]
    creado_en: datetime
