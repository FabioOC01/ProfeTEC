# Backend — ProfeTEC.IA

FastAPI + Python 3.11.

## Arranque local

```bash
python -m venv .venv
source .venv/Scripts/activate    # Windows Git Bash (o .venv\Scripts\activate.bat en cmd)
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8080
```

- Docs interactivas: http://localhost:8080/docs
- Health: http://localhost:8080/health

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
│   ├── main.py          Punto de entrada FastAPI
│   ├── config.py        Settings (Pydantic)
│   ├── core/            (módulos transversales: auth, vertex, firestore — sprints 1+)
│   └── routers/
│       └── health.py
├── tests/
│   └── test_health.py
├── Dockerfile
├── requirements.txt
└── pytest.ini
```
