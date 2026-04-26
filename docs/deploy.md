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
  storage.googleapis.com

# Repositorio Artifact Registry (una sola vez)
gcloud artifacts repositories create profetec \
  --repository-format=docker \
  --location=$REGION
```

## 2. Desplegar backend

```bash
cd backend

gcloud run deploy profetec-backend \
  --source . \
  --region $REGION \
  --allow-unauthenticated \
  --set-env-vars APP_ENV=production,CORS_ORIGINS=https://profetec-frontend-XXX.run.app
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
