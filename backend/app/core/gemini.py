"""
Generación de respuestas con Gemini Flash (RF-13..RF-17).
Import lazy para que los tests corran sin google-cloud-aiplatform instalado.
Usa credenciales explícitas del service account.
"""
import os

from app.config import settings

_model = None
MODEL_ID = "gemini-1.5-flash-002"

SYSTEM_PROMPT = (
    "Eres ProfeTEC.IA, un asistente tutor virtual del Instituto TECSUP. "
    "Tu función es ayudar a los estudiantes a comprender el material de sus cursos.\n\n"
    "REGLAS IMPORTANTES:\n"
    "1. Responde ÚNICAMENTE con información del contexto del material del curso proporcionado.\n"
    "2. Si la información no está en el contexto, di: "
    "'Esta información no se encuentra en el material del curso disponible.'\n"
    "3. Cita siempre la fuente al final de cada idea relevante con el formato: "
    "[📄 {nombre_documento}, pág. {pagina}]\n"
    "4. Responde en español con tono didáctico y amigable.\n"
    "5. Sé conciso pero completo. Usa listas o pasos cuando facilite la comprensión.\n"
    "6. No inventes información ni uses conocimiento externo al contexto."
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


def generar_respuesta(pregunta: str, chunks: list[dict]) -> str:
    """
    Construye el prompt con los chunks como contexto y genera la respuesta via Gemini.
    Si no hay chunks relevantes, retorna un mensaje estándar.
    """
    if not chunks:
        return (
            "No encontré información relevante en el material del curso "
            "para responder tu pregunta. Intenta reformularla o consulta a tu docente."
        )

    # Construir contexto enumerado
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

    model = _get_model()
    response = model.generate_content(prompt)
    return response.text
