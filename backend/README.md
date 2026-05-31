# Backend — ProfeTEC.IA

API REST en **FastAPI + Python 3.11**. Expone autenticación, cursos, ingesta de documentos,
chat RAG con Gemini y quizzes generados por IA.

## Arranque local

```bash
python -m venv .venv
source .venv/Scripts/activate    # Windows Git Bash (o .venv\Scripts\activate.bat en cmd)
pip install -r requirements.txt
cp .env.example .env             # rellenar con tus credenciales
uvicorn app.main:app --reload --port 8080
```

- Docs interactivas (Swagger): http://localhost:8080/docs
- Health: http://localhost:8080/health

## Configuración (`.env`)

Variables principales (ver [`.env.example`](.env.example) para la lista completa):

| Variable | Descripción |
|---|---|
| `CORS_ORIGINS` | Orígenes permitidos (frontend). En local: `http://localhost:5174`. |
| `ALLOWED_EMAIL_DOMAINS` | Dominios institucionales permitidos. `*` para abrir en demos. |
| `FIREBASE_PROJECT_ID` / `GOOGLE_APPLICATION_CREDENTIALS` | Proyecto y service account de Firebase/GCP. |
| `GCP_PROJECT_ID` / `GCP_REGION` / `GCS_BUCKET_NAME` | Vertex AI (Gemini + embeddings) y almacenamiento. |
| `RAG_BACKEND` | `firestore_scan` (local/demo) o `bigquery_vector` (BigQuery `VECTOR_SEARCH`). |
| `RAG_TOP_K`, `RAG_SCORE_MINIMO`, `RAG_MAX_CHUNKS_SCAN` | Ajustes de recuperación. |
| `BIGQUERY_DATASET`, `BIGQUERY_CHUNKS_TABLE`, `BIGQUERY_LOCATION` | Solo si `RAG_BACKEND=bigquery_vector`. |

## Tests

```bash
pytest -v
```

## Build de imagen Docker

```bash
docker build -t profetec-backend .
docker run -p 8080:8080 --env-file .env profetec-backend
```

## Estructura

```
backend/
├── app/
│   ├── main.py              Punto de entrada FastAPI (monta routers + CORS)
│   ├── config.py            Settings (Pydantic Settings, lee .env)
│   ├── core/                Módulos transversales
│   │   ├── auth.py          Verificación de token Firebase
│   │   ├── access.py        Validación de dominio, roles y acceso a cursos
│   │   ├── firebase.py / firestore_client.py   Inicialización y cliente Firestore
│   │   ├── storage.py       Cloud Storage (PDFs)
│   │   ├── extractor.py / chunker.py           Extracción de texto + chunking
│   │   ├── vertex.py        Embeddings (text-embedding-004)
│   │   ├── gemini.py        Generación con Gemini 2.5 Flash (modos directo/socrático)
│   │   ├── rag.py           Pipeline RAG (firestore_scan)
│   │   ├── bigquery_rag.py  Recuperación vía BigQuery Vector Search
│   │   └── quiz_generator.py  Generación de quizzes con IA
│   ├── models/              Esquemas Pydantic (usuario, curso, documento, mensaje, quiz)
│   └── routers/
│       ├── health.py        Healthcheck
│       ├── auth_router.py   Perfil + onboarding por rol
│       ├── cursos.py        CRUD de cursos + matrícula
│       ├── documentos.py    Ingesta de material académico
│       ├── chat.py          Chat RAG (streaming SSE), feedback y analítica
│       └── quiz.py          Crear/resolver/calificar quizzes
├── tests/                   Pruebas con pytest (auth, cursos, documentos, chat, rag, quiz, …)
├── Dockerfile
├── requirements.txt
└── pytest.ini
```

## Despliegue

Ver la guía de Cloud Run en [`../docs/deploy.md`](../docs/deploy.md).
