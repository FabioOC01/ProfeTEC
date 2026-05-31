from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

ModoChat = Literal["directo", "socratico"]


class ChatRequest(BaseModel):
    pregunta: str = Field(..., min_length=1, max_length=2000)
    conversacion_id: Optional[str] = None
    modo: ModoChat = "directo"


class ChunkCitado(BaseModel):
    documento_id: str
    nombre_doc: str
    pagina: int
    fragmento: str  # primeros 200 chars del chunk


class ChatResponse(BaseModel):
    respuesta: str
    conversacion_id: str
    mensaje_id: str
    modo: ModoChat = "directo"
    chunks_usados: list[ChunkCitado]
    creado_en: datetime


class FeedbackRequest(BaseModel):
    valor: Literal["positivo", "negativo"]
    comentario: Optional[str] = Field(default=None, max_length=500)


class FeedbackResponse(BaseModel):
    mensaje_id: str
    feedback_valor: Literal["positivo", "negativo"]
    feedback_comentario: Optional[str] = None


class MensajeOut(BaseModel):
    id: str
    pregunta: str
    respuesta: str
    modo: ModoChat = "directo"
    chunks_usados: list[ChunkCitado]
    creado_en: datetime
    feedback_valor: Optional[Literal["positivo", "negativo"]] = None
    feedback_comentario: Optional[str] = None


class ConversacionOut(BaseModel):
    id: str
    titulo: str
    actualizado_en: datetime


class CursoAnalyticsResponse(BaseModel):
    curso_id: str
    total_mensajes: int
    total_conversaciones: int
    total_documentos: int
    total_chunks: int
    estudiantes_matriculados: int
    feedback_positivo: int
    feedback_negativo: int
    feedback_pendiente: int
    total_quizzes: int = 0
    total_intentos_quiz: int = 0
    promedio_aciertos_quiz: float = 0.0
    mensajes_directo: int = 0
    mensajes_socratico: int = 0
    feedback_positivo_directo: int = 0
    feedback_negativo_directo: int = 0
    feedback_positivo_socratico: int = 0
    feedback_negativo_socratico: int = 0
    rag_backend: str = "firestore_scan"
