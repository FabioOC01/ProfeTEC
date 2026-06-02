# Construye y despliega el frontend (React/Vite) a Cloud Run.
# Uso:  .\deploy-frontend.ps1
# Necesita los build args VITE_* porque Vite los hornea en el bundle al compilar.

$ErrorActionPreference = "Stop"

$PROJECT_ID  = "profetec-ia-4229d"
$REGION      = "us-central1"
$BACKEND_URL = "https://profetec-backend-102227161361.us-central1.run.app"
$IMAGE       = "us-central1-docker.pkg.dev/$PROJECT_ID/cloud-run-source-deploy/profetec-frontend:latest"
$FRONTEND    = Join-Path $PSScriptRoot "frontend"

# Config Web de Firebase (no es secreta: viaja al navegador).
$SUBS = @(
    "_VITE_API_URL=$BACKEND_URL"
    "_VITE_FIREBASE_API_KEY=AIzaSyAF4fgrnH98u_i4s8o5C0ayX9dcZxS9p4E"
    "_VITE_FIREBASE_AUTH_DOMAIN=$PROJECT_ID.firebaseapp.com"
    "_VITE_FIREBASE_PROJECT_ID=$PROJECT_ID"
    "_VITE_FIREBASE_APP_ID=1:102227161361:web:7b112aaf5075b2ef061cb0"
) -join ","

Push-Location $FRONTEND
try {
    Write-Host "==> 1/2 Construyendo imagen con build args (Cloud Build) ..." -ForegroundColor Cyan
    gcloud builds submit --config cloudbuild.yaml --substitutions $SUBS

    Write-Host "==> 2/2 Desplegando imagen a Cloud Run ..." -ForegroundColor Cyan
    gcloud run deploy profetec-frontend `
        --image $IMAGE `
        --region $REGION `
        --allow-unauthenticated
}
finally {
    Pop-Location
}

Write-Host "==> Listo. Abrir (Ctrl+Shift+R para evitar cache):" -ForegroundColor Green
Write-Host "    https://profetec-frontend-102227161361.us-central1.run.app"
