"""
Generación de respuestas con Gemini Flash (RF-13..RF-17).
Import lazy para que los tests corran sin google-cloud-aiplatform instalado.
Usa credenciales explícitas del service account.
"""
import os

from app.config import settings

_model = None
MODEL_ID = "gemini-2.5-flash"

SYSTEM_PROMPT = (
    "Eres ProfeTEC.IA, un asistente tutor virtual del Instituto TECSUP. "
    "Tu función principal es ayudar a los estudiantes a comprender el material de sus cursos.\n\n"
    "CÓMO RESPONDER SEGÚN EL TIPO DE PREGUNTA:\n\n"
    "A) SALUDOS Y PREGUNTAS SOBRE TI (ej: 'hola', '¿quién eres?', '¿qué puedes hacer?'):\n"
    "   Responde de forma amigable y breve presentándote como ProfeTEC.IA, tutor virtual "
    "de TECSUP. Explica que puedes ayudar con dudas sobre el material del curso. "
    "No necesitas citar fuentes para este tipo de respuestas.\n\n"
    "B) PREGUNTAS ACADÉMICAS SOBRE EL CONTENIDO DEL CURSO:\n"
    "   1. Responde ÚNICAMENTE con información del contexto proporcionado.\n"
    "   2. Si la información no está en el contexto, di: "
    "'Esta información no se encuentra en el material del curso disponible.'\n"
    "   3. Cita la fuente al final de cada idea relevante con el formato: "
    "[📄 {nombre_documento}, pág. {pagina}]\n"
    "   4. No inventes información ni uses conocimiento externo al contexto.\n\n"
    "REGLAS GENERALES:\n"
    "- Responde siempre en español con tono didáctico y amigable.\n"
    "- Sé conciso pero completo. Usa listas o pasos cuando facilite la comprensión."
)


def _get_model():
    global _model
    if _model is None:
        import vertexai
        from vertexai.generative_models import GenerativeModel

        project = settings.gcp_project_id or settings.firebase_project_id
        location = settings.gcp_region

        cred_path = settings.google_application_credentials or os.environ.get(
            "GOOGLE_APPLICATION_CREDENTIALS"
        )
        credentials = None
        if cred_path and os.path.exists(cred_path):
            from google.oauth2 import service_account

            credentials = service_account.Credentials.from_service_account_file(
                cred_path,
                scopes=["https://www.googleapis.com/auth/cloud-platform"],
            )

        vertexai.init(project=project, location=location, credentials=credentials)
        _model = GenerativeModel(MODEL_ID, system_instruction=SYSTEM_PROMPT)
    return _model


# Configuración de generación — controla longitud y creatividad
GENERATION_CONFIG = {
    "max_output_tokens": 512,   # ~350-400 palabras máximo
    "temperature": 0.3,          # bajo = más factual, menos creativo
    "top_p": 0.9,
}


def generar_respuesta(pregunta: str, chunks: list[dict]) -> str:
    """
    Construye el prompt y genera la respuesta via Gemini.
    Si hay chunks, los usa como contexto (pregunta académica).
    Si no hay chunks, deja que Gemini decida (saludo, presentación, o fuera de alcance).
    """
    if chunks:
        partes_contexto = []
        for i, chunk in enumerate(chunks, 1):
            partes_contexto.append(
                f"[Fragmento {i} — {chunk['nombre_doc']}, pág. {chunk['pagina']}]\n"
                f"{chunk['texto']}"
            )
        contexto = "\n\n---\n\n".join(partes_contexto)

        prompt = (
            f"Contexto del material del curso:\n\n"
            f"{contexto}\n\n"
            f"---\n\n"
            f"Pregunta del estudiante: {pregunta}\n\n"
            f"Responde basándote únicamente en el contexto anterior, "
            f"citando las fuentes con el formato indicado."
        )
    else:
        # Sin contexto: el modelo decide si es saludo, presentación o pregunta fuera de alcance
        prompt = (
            f"Mensaje del estudiante: {pregunta}\n\n"
            f"No hay contexto del material del curso que coincida con esta pregunta. "
            f"Si es un saludo o una pregunta sobre ti, responde amigablemente siguiendo las reglas. "
            f"Si es una pregunta académica, indica que la información no está en el material disponible."
        )

    model = _get_model()
    response = model.generate_content(prompt, generation_config=GENERATION_CONFIG)
    return response.text
