"""Modelos para el módulo de quizzes (RF-20..RF-23)."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class PreguntaQuiz(BaseModel):
    """Una pregunta de opción múltiple generada a partir del material del curso."""
    texto: str = Field(..., min_length=1, max_length=600)
    opciones: list[str] = Field(..., min_length=2, max_length=5)
    indice_correcto: int = Field(..., ge=0)
    explicacion: Optional[str] = Field(default=None, max_length=500)
    nombre_doc: Optional[str] = Field(default=None, max_length=200)
    pagina: Optional[int] = Field(default=None, ge=0)


class PreguntaParaResponder(BaseModel):
    """Pregunta servida al estudiante: sin indicar cuál es la correcta."""
    texto: str
    opciones: list[str]
    nombre_doc: Optional[str] = None
    pagina: Optional[int] = None


class QuizCreate(BaseModel):
    """Solicitud de generación de quiz."""
    titulo: str = Field(..., min_length=1, max_length=120)
    tema: Optional[str] = Field(default=None, max_length=300)
    num_preguntas: int = Field(default=5, ge=3, le=10)
    semana_desde: Optional[int] = Field(default=None, ge=1, le=30)
    semana_hasta: Optional[int] = Field(default=None, ge=1, le=30)


class QuizResumen(BaseModel):
    id: str
    titulo: str
    tema: Optional[str] = None
    num_preguntas: int
    semana_desde: Optional[int] = None
    semana_hasta: Optional[int] = None
    creado_en: datetime


class QuizDetalleDocente(BaseModel):
    """Vista completa del quiz, incluida la respuesta correcta. Solo para el docente."""
    id: str
    curso_id: str
    titulo: str
    tema: Optional[str] = None
    semana_desde: Optional[int] = None
    semana_hasta: Optional[int] = None
    preguntas: list[PreguntaQuiz]
    creado_en: datetime


class QuizParaTomar(BaseModel):
    """Vista del quiz para el estudiante: sin revelar cuál es la opción correcta."""
    id: str
    curso_id: str
    titulo: str
    tema: Optional[str] = None
    semana_desde: Optional[int] = None
    semana_hasta: Optional[int] = None
    preguntas: list[PreguntaParaResponder]


class IntentoCreate(BaseModel):
    """Respuestas del estudiante. respuestas[i] = índice de opción elegido para la pregunta i."""
    respuestas: list[int] = Field(..., min_length=1)


class DetallePregunta(BaseModel):
    """Resultado por pregunta tras corregir un intento."""
    indice_pregunta: int
    texto: str
    opciones: list[str]
    elegida: int
    correcta: int
    es_correcta: bool
    explicacion: Optional[str] = None


class IntentoResultado(BaseModel):
    """Resultado completo de un intento, devuelto al estudiante tras enviar respuestas."""
    id: str
    quiz_id: str
    correctas: int
    total_preguntas: int
    porcentaje: float
    detalle: list[DetallePregunta]
    completado_en: datetime


class IntentoResumen(BaseModel):
    """Resumen de un intento (sin desglose por pregunta), para listados."""
    id: str
    quiz_id: str
    usuario_id: str
    usuario_nombre: Optional[str] = None
    correctas: int
    total_preguntas: int
    porcentaje: float
    completado_en: datetime
