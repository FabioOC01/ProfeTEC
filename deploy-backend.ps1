# Despliega el backend (FastAPI) a Cloud Run.
# Uso:  .\deploy-backend.ps1
# Las variables de entorno ya configuradas en el servicio se conservan.

$ErrorActionPreference = "Stop"

$REGION  = "us-central1"
$BACKEND = Join-Path $PSScriptRoot "backend"

Write-Host "==> Desplegando backend desde $BACKEND ..." -ForegroundColor Cyan

Push-Location $BACKEND
try {
    gcloud run deploy profetec-backend `
        --source . `
        --region $REGION `
        --allow-unauthenticated
}
finally {
    Pop-Location
}

Write-Host "==> Listo. Probar salud:" -ForegroundColor Green
Write-Host "    curl https://profetec-backend-102227161361.us-central1.run.app/health"
