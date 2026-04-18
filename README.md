# ProfeTEC.IA

Tutor virtual basado en IA para estudiantes de TECSUP. Arquitectura RAG multimodal sobre Gemini (Vertex AI), con FastAPI + React + Firestore + Firebase Auth, desplegado en Cloud Run.

Proyecto de tesis — Orlando Fabio Ochoa Cuenca, TECSUP, carrera de Diseño y Desarrollo de Software.

## Estado

**Sprint 0 — Bootstrap** (esqueletos y `/health` funcionando).

Hoja de ruta completa en [`docs/sprints.md`](docs/sprints.md).

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
| LLM | Gemini vía Vertex AI |
| Almacenamiento | Cloud Storage |
| Despliegue | Cloud Run |

## Licencia

Uso académico — ver [`LICENSE`](LICENSE).
