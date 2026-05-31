# ProfeTEC.IA

Tutor virtual basado en IA para estudiantes de TECSUP. Arquitectura RAG multimodal sobre Gemini (Vertex AI), con FastAPI + React + Firestore + Firebase Auth, desplegado en Cloud Run.

Proyecto de tesis — Orlando Fabio Ochoa Cuenca, TECSUP, carrera de Diseño y Desarrollo de Software.


## Estructura

```
ProfeTEC/
├── backend/        FastAPI (Python 3.11+)
├── frontend/       React 19 + Vite
├── docs/           Documentación de sprints y arquitectura
└── .github/        CI (GitHub Actions)
```

## Requisitos

- Python 3.11 o superior
- Node.js 20 o superior
- Git
- Cuenta Google Cloud (para sprints siguientes)

## Arranque rápido (local)

### Backend

```bash
cd backend
python -m venv .venv
source .venv/Scripts/activate    # Windows Git Bash
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8080
```

Verificar: `curl http://localhost:8080/health`

### Frontend

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

Abrir `http://localhost:5173`.

## Stack declarado (tesis)

| Capa | Tecnología |
|---|---|
| Frontend | React 19, Vite, Axios |
| Backend | Python 3.11, FastAPI, Pydantic v2 |
| Base de datos | Firestore |
| Autenticación | Firebase Auth (Google) |
| LLM | Gemini 2.5 Flash vía Vertex AI |
| Embeddings | text-embedding-004 (768 dims) |
| Almacenamiento | Cloud Storage |
| Búsqueda vectorial | Firestore scan local o BigQuery Vector Search |
| Despliegue | Cloud Run |

## Funcionalidades implementadas

- Login con Google + onboarding por rol (docente / estudiante).
- Restricción por dominio institucional configurable (`ALLOWED_EMAIL_DOMAINS`).
- CRUD de cursos + matrícula por código.
- Carga de material académico (PDF, PPTX, TXT) + pipeline RAG.
- Chat con citas explícitas al material del docente.
- **Dos modos pedagógicos en el chat**: directo (respuestas explicativas) y socrático
  (preguntas guía que llevan al estudiante a la respuesta).
- **RAG configurable**: `firestore_scan` para local/demo y `bigquery_vector` para
  recuperar chunks mediante BigQuery `VECTOR_SEARCH`.
- **Quizzes generados automáticamente** a partir del material del curso: el docente crea,
  los estudiantes resuelven y reciben corrección con explicaciones.
- Feedback 👍/👎 por respuesta + analítica docente (mensajes, conversaciones, documentos,
  feedback, mensajes por modo, intentos, promedio de aciertos de quizzes y backend RAG activo).

## Licencia

Uso académico — ver [`LICENSE`](LICENSE).
