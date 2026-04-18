# Siguientes pasos — Sprint 0 a Sprint 1

Acciones manuales requeridas del tesista (no se pueden automatizar desde código).

## A. GitHub (hoy mismo)

1. Crear repositorio **privado** en GitHub: `profetec-ia` (o similar).
2. Enlazar el repo local y hacer el primer push:
   ```bash
   cd C:/Users/FabioPC/Documents/ProfeTEC
   git remote add origin https://github.com/<tu-usuario>/profetec-ia.git
   git branch -M main
   git push -u origin main
   ```
3. Activar **GitHub Actions** en el repo (Settings → Actions → permitir).
4. Crear rama `develop` para trabajo diario:
   ```bash
   git checkout -b develop
   git push -u origin develop
   ```

## B. Google Cloud (esta semana)

1. Crear un proyecto en https://console.cloud.google.com/ llamado `profetec-ia`.
2. Habilitar facturación (se puede usar la cuenta de crédito de $300 para estudiantes).
3. Instalar Google Cloud SDK: https://cloud.google.com/sdk/docs/install
4. Seguir la guía en [`docs/deploy.md`](deploy.md) → secciones 1, 2 y 3.

## C. Firebase (Sprint 1, pero configurar ya)

1. Ir a https://console.firebase.google.com/ y agregar Firebase al proyecto GCP creado.
2. Activar **Authentication** → Google provider.
3. Activar **Firestore Database** (modo de prueba temporal).
4. Registrar una "Web App" → copiar el objeto `firebaseConfig` → añadir sus valores al `.env.local` del frontend.
5. Descargar una *service account key* (Settings → Service Accounts → Generate new private key) → **guardarla fuera del repo** (en `~/secrets/` o similar) → referenciarla en `GOOGLE_APPLICATION_CREDENTIALS` del backend.

## D. Trello (para cumplir el Cap. 4)

1. Crear tablero `ProfeTEC.IA – Backlog`.
2. Columnas: **Backlog · Sprint actual · En progreso · Code review · Done**.
3. Crear una tarjeta por cada RF priorizado (ver tabla de RFs en la evaluación).
4. Compartir el tablero con la asesora (modo lectura).
5. Exportar captura al cierre de cada sprint → guardar en `docs/evidencia/sprint-N/`.

## E. Bitácora académica semanal

Crear en `docs/bitacora/YYYY-Www.md` una nota corta cada viernes con:

- Qué se hizo esta semana.
- Qué quedó pendiente.
- Bloqueos.
- Decisiones técnicas tomadas y por qué.

Esto alimenta las secciones "Retrospectiva" del Cap. 4.

## F. Correos a la asesora

1. Hoy: confirmar extensión de plazos y compartir el plan de sprints.
2. Viernes: enviar bitácora semanal + capturas del avance.
3. Antes del Sprint 4: agendar revisión intermedia para validar el hito del 50 %.
