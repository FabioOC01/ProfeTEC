# Hoja de ruta de sprints — ProfeTEC.IA

| Sprint | Duración | Objetivo | RFs cubiertos | Entregable verificable |
|---|---|---|---|---|
| **0 — Setup** | 1 sem | Repo, esqueleto backend/frontend, deploy "hello world" | — | `/health` respondiendo en Cloud Run |
| **1 — Auth e Infra** | 2 sem | Firebase Auth (Google), roles, middleware, CRUD cursos | RF-01, RF-02, RF-03, RF-05 | Login Google + curso creado por docente |
| **2 — Ingesta** | 2 sem | Upload → extracción → chunking → embeddings → índice | RF-07, RF-08, RF-09, RF-10, RF-11, RF-12 | Documento subido e indexado |
| **3 — RAG + Chat** | 2 sem | Endpoint `/chat` con retrieval + Gemini + citas | RF-13, RF-14, RF-15, RF-16, RF-18 | Pregunta → respuesta con cita |
| **4 — Frontend integrado (50 %)** | 2 sem | UI completa docente/estudiante conectada | — (integración) | **Demo end-to-end desplegada** |
| 5 — Tutor Socrático | 2 sem | Refinamiento del system prompt | RF-17 | A/B directo vs. socrático |
| 6 — Quizzes | 2 sem | Generación y corrección automática | RF-20 a RF-23 | Quiz generado y corregido |
| 7 — Analítica + Feedback | 2 sem | Panel docente, feedback 👍/👎 | RF-24, RF-25 | Panel con datos reales |
| 8 — Hardening | 2 sem | Tests, seguridad, documentación, piloto | RNF-01 a RNF-08 | Suite de tests + docs + piloto |

Hito **50 %** = fin de Sprint 4. Hito **100 %** = fin de Sprint 8.
