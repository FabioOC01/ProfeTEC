# Hoja de ruta de sprints — ProfeTEC.IA

| Sprint | Duración | Objetivo | RFs cubiertos | Entregable verificable | Estado |
|---|---|---|---|---|---|
| **0 — Setup** | 1 sem | Repo, esqueleto backend/frontend, deploy "hello world" | — | `/health` respondiendo en Cloud Run | ✅ |
| **1 — Auth e Infra** | 2 sem | Firebase Auth (Google), roles, middleware, CRUD cursos | RF-01, RF-02, RF-03, RF-05 | Login Google + curso creado por docente | ✅ |
| **2 — Ingesta** | 2 sem | Upload → extracción → chunking → embeddings → índice | RF-07, RF-08, RF-09, RF-10, RF-11, RF-12 | Documento subido e indexado | ✅ |
| **3 — RAG + Chat** | 2 sem | Endpoint `/chat` con retrieval + Gemini + citas | RF-13, RF-14, RF-15, RF-16, RF-18 | Pregunta → respuesta con cita | ✅ |
| **4 — Frontend integrado (50 %)** | 2 sem | UI completa docente/estudiante conectada | — (integración) | **Demo end-to-end desplegada** | ✅ |
| **5 — Tutor Socrático** | 2 sem | Doble system prompt (directo / socrático) + toggle por mensaje | RF-17 | Comparación directa vs socrática en vivo | ✅ |
| **6 — Quizzes** | 2 sem | Generación de preguntas desde RAG + corrección automática | RF-20 a RF-23 | Quiz generado, resuelto y corregido | ✅ |
| **7 — Analítica + Feedback** | 2 sem | Panel docente, feedback 👍/👎 + métricas por modo y quiz | RF-24, RF-25 | Panel con datos reales | ✅ |
| **8 — Hardening** | 2 sem | Tests, seguridad, documentación, piloto | RNF-01 a RNF-08 | Suite de tests + docs + piloto | ✅ |
| **9 — RAG escalable + Socrático** | 1 sem | BigQuery Vector Search + modo socrático real | RF-17, RNF-02 | Chat con modo socrático y RAG configurable | ✅ |

Hito **50 %** = fin de Sprint 4. Hito **100 %** = fin de Sprint 8.

## Detalle de Sprints 5, 6 y 8 (entregados post-MVP)

### Sprint 5 — Tutor Socrático

- `backend/app/core/gemini.py` mantiene dos `system_instruction` independientes:
  `SYSTEM_PROMPT_DIRECTO` y `SYSTEM_PROMPT_SOCRATICO`. La función
  `generar_respuesta(pregunta, chunks, modo)` selecciona el modelo cacheado según el modo.
- `ChatRequest` acepta el campo `modo: "directo" | "socratico"` (default `directo`).
- El frontend ya tenía un `ModeToggle` en sessionStorage; ahora se propaga al backend
  (`enviarPregunta(cursoId, pregunta, conversacionId, modo)`).
- Cada mensaje persiste el modo en Firestore (`mensajes.modo`).
- La analítica del curso reporta `mensajes_directo` y `mensajes_socratico` para
  comparación A/B.

### Sprint 9 — BigQuery Vector Search

- Firestore sigue como fuente operativa del sistema.
- BigQuery almacena una copia denormalizada de chunks y embeddings para busqueda
  semantica con `VECTOR_SEARCH`.
- `RAG_BACKEND=firestore_scan` conserva el flujo local/simple.
- `RAG_BACKEND=bigquery_vector` usa BigQuery y vuelve automaticamente a Firestore
  si BigQuery no esta disponible, evitando romper la demo.
- La ingesta de documentos escribe chunks en Firestore y los indexa en BigQuery de
  forma best-effort; la eliminacion de documentos intenta limpiar ambos indices.

### Sprint 6 — Quizzes

- Nuevo router `backend/app/routers/quiz.py` con seis endpoints autenticados:
  - `POST   /cursos/{id}/quizzes`                       (docente: genera quiz)
  - `GET    /cursos/{id}/quizzes`                       (lista quizzes del curso)
  - `GET    /cursos/{id}/quizzes/{quiz_id}`             (detalle; docente ve respuestas)
  - `DELETE /cursos/{id}/quizzes/{quiz_id}`             (docente dueño elimina)
  - `POST   /cursos/{id}/quizzes/{quiz_id}/intentos`    (estudiante envía respuestas)
  - `GET    /cursos/{id}/quizzes/{quiz_id}/intentos`    (docente: todos; estudiante: los suyos)
- Generación en `backend/app/core/quiz_generator.py`: recupera chunks vía RAG (o
  muestreo si no hay tema), pide a Gemini un JSON con preguntas de opción múltiple
  y valida cada pregunta antes de persistirla.
- Colecciones nuevas en Firestore: `quizzes`, `quiz_intentos`.
- Frontend: páginas `QuizzesPage` (listado + creación) y `QuizDetallePage`
  (resolución del estudiante o vista completa del docente con sus intentos).
- Analítica extendida con `total_quizzes`, `total_intentos_quiz` y
  `promedio_aciertos_quiz`.

### Sprint 8 — Hardening

- Suite de pruebas backend validada con `pytest -q`, agrega cobertura de:
  - Modos pedagógicos del chat (`test_chat.py`, `test_gemini_modos.py`).
  - Quizzes: creación, permisos, corrección, intentos y validaciones
    (`test_quiz.py`, `test_quiz_generator.py`).
- Test de dominio institucional aislado de la configuración local
  (`test_auth.py::test_rechaza_correo_no_institucional` ahora usa `monkeypatch`).
- Seguridad de endpoints nuevos: cada endpoint de quiz aplica
  `verificar_acceso_curso` + checks adicionales por rol y por pertenencia del
  recurso al curso de la URL.
