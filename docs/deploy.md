# Guía de despliegue — Cloud Run

Pasos para poner en línea el backend y el frontend de ProfeTEC.IA. Requiere cuenta Google Cloud activa y `gcloud` autenticado.

## 1. Configuración inicial (una sola vez)

```bash
# Login
gcloud auth login
gcloud auth application-default login

# Proyecto (ajustar el ID)
export PROJECT_ID=profetec-ia
export REGION=us-central1

gcloud projects create $PROJECT_ID --name="ProfeTEC.IA"
gcloud config set project $PROJECT_ID
gcloud config set run/region $REGION

# APIs necesarias
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  firestore.googleapis.com \
  aiplatform.googleapis.com \
  firebase.googleapis.com \
  identitytoolkit.googleapis.com \
  storage.googleapis.com \
  bigquery.googleapis.com

# Repositorio Artifact Registry (una sola vez)
gcloud artifacts repositories create profetec \
  --repository-format=docker \
  --location=$REGION
```

## 2. Desplegar backend

Si se usara BigQuery Vector Search, crear primero el dataset, tabla e indice:

```bash
bq --location=US mk --dataset $PROJECT_ID:profetec_rag

bq query --use_legacy_sql=false "
CREATE TABLE IF NOT EXISTS \`$PROJECT_ID.profetec_rag.chunks\` (
  chunk_id STRING NOT NULL,
  curso_id STRING NOT NULL,
  documento_id STRING NOT NULL,
  nombre_doc STRING,
  texto STRING,
  pagina INT64,
  posicion INT64,
  embedding ARRAY<FLOAT64>,
  created_at TIMESTAMP
)
CLUSTER BY curso_id, documento_id"

bq query --use_legacy_sql=false "
CREATE VECTOR INDEX IF NOT EXISTS idx_chunks_embedding
ON \`$PROJECT_ID.profetec_rag.chunks\`(embedding)
OPTIONS(distance_type = 'COSINE', index_type = 'IVF')"
```

```bash
cd backend

gcloud run deploy profetec-backend \
  --source . \
  --region $REGION \
  --allow-unauthenticated \
  --set-env-vars APP_ENV=production,CORS_ORIGINS=https://profetec-frontend-XXX.run.app,RAG_BACKEND=bigquery_vector,BIGQUERY_DATASET=profetec_rag,BIGQUERY_CHUNKS_TABLE=chunks,BIGQUERY_LOCATION=US
```

Cloud Run devolverá una URL tipo `https://profetec-backend-xxxxx-uc.a.run.app`. Probar:

```bash
curl https://profetec-backend-xxxxx-uc.a.run.app/health
```

## 3. Desplegar frontend

```bash
cd frontend

export BACKEND_URL=https://profetec-backend-xxxxx-uc.a.run.app

gcloud run deploy profetec-frontend \
  --source . \
  --region $REGION \
  --allow-unauthenticated \
  --build-env-vars VITE_API_URL=$BACKEND_URL
```

Después, volver al backend y actualizar `CORS_ORIGINS` con la URL real del frontend.

## 4. Verificación del hito Sprint 0

- [ ] `GET /health` del backend devuelve `status: "ok"`.
- [ ] Frontend desplegado muestra la respuesta JSON del backend.
- [ ] Ambas URLs accesibles públicamente.
- [ ] Capturas de pantalla guardadas en `docs/evidencia/sprint-0/`.
