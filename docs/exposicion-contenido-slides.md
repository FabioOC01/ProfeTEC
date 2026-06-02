# Contenido para slides — Exposición ProfeTEC.IA

Texto listo para pegar en cada slide. **Bullets** = lo que va escrito en pantalla (corto). **Notas** = lo que vas a decir tú (no se proyecta).

Reglas:
- Máximo 6 bullets por slide, ≤ 8 palabras cada uno.
- Tipografía mínima 24pt en cuerpo, 32pt en títulos.
- 1 idea visual por slide (diagrama, tabla, foto o screenshot — no muros de texto).

---

## SLIDE 1 — Portada (20s)

**Título grande:**
> ProfeTEC.IA — Tutor virtual con IA para estudiantes de TECSUP

**Subtítulo:**
> Implementación de un chatbot con Inteligencia Artificial especializado en educación

**Pie:**
- Orlando Fabio Ochoa Cuenca
- Diseño y Desarrollo de Software — TECSUP
- Asesor: [nombre]
- Junio 2026

**Notas:** "Buenos días, mi nombre es Fabio Ochoa, de la carrera de Diseño y Desarrollo de Software. Hoy presento ProfeTEC.IA, un tutor virtual con inteligencia artificial diseñado para estudiantes de TECSUP."

---

## SLIDE 2 — Problemática (60s)

**Título:** El problema: tutoría 1-a-1 no escala

**Bullets:**
- 30+ estudiantes por docente: dudas sin resolver fuera del aula.
- Material disperso (PDFs, PPTs, Drive, WhatsApp) → difícil consultar a destiempo.
- Tutorías presenciales: horario limitado, no asincrónicas.
- Soluciones genéricas (ChatGPT) no conocen el material del curso ni siguen método pedagógico.

**Visual:** Ícono de docente con muchas flechas hacia estudiantes + reloj.

**Notas:** "El problema central es que la tutoría personalizada no escala. Un docente atiende a 30+ alumnos, el material está disperso, y las herramientas genéricas como ChatGPT no conocen el material específico del curso ni aplican un método pedagógico — simplemente dan la respuesta. Esto último es importante: estamos formando ingenieros, no copistas."

---

## SLIDE 3 — Objetivos y alcance (60s)

**Título:** Objetivos

**Objetivo general:**
> Implementar un tutor virtual basado en IA generativa que responda dudas de estudiantes de TECSUP usando exclusivamente el material académico del curso, con dos modos pedagógicos.

**Objetivos específicos:**
1. Construir un pipeline RAG sobre Gemini con citas verificables al material.
2. Ofrecer modos pedagógicos **Directo** y **Socrático** seleccionables por el estudiante.
3. Generar y corregir quizzes automáticamente desde el material del curso.
4. Entregar analítica al docente sobre uso, feedback y aciertos.

**Alcance:**
| ✅ SÍ incluye | ❌ NO incluye |
|---|---|
| Texto (PDF, PPTX, TXT) | Imágenes/audio/video |
| Español | Otros idiomas |
| Web (responsive) | App móvil nativa |
| Cursos individuales | Integración LMS (Moodle/Canvas) |

**Notas:** "El objetivo es un tutor que use SOLO el material del docente, con citas, y que pueda enseñar de dos maneras: directa o socrática. El alcance es texto en español vía web; queda fuera multimedia, otros idiomas y la integración con LMS, que dejo como trabajo futuro."

---

## SLIDE 4 — Requerimientos funcionales (60s)

**Título:** 25 RFs agrupados en 5 épicas

| Épica | RFs | Qué hace |
|---|---|---|
| **Auth + Gestión** | RF-01 a RF-06 | Login Google, roles, cursos, matrícula |
| **Ingesta** | RF-07 a RF-12 | Subida PDF/PPTX, chunking, embeddings |
| **Chat RAG** | RF-13 a RF-18 | Búsqueda semántica, Gemini, citas, modo dual |
| **Quizzes** | RF-20 a RF-23 | Generación IA, resolución, corrección |
| **Analítica + Feedback** | RF-24 a RF-25 | Métricas docente, 👍/👎 por respuesta |

**Notas:** "Los 25 requerimientos se agrupan en 5 épicas. La diferenciadora es la tercera — Chat RAG — porque incluye el modo dual Directo/Socrático que no existe en chatbots genéricos."

---

## SLIDE 5 — Arquitectura (90s) — SLIDE CLAVE

**Título:** Arquitectura RAG multimodal

**Visual:** Diagrama simplificado (versión reducida de `arquitectura-rag.md`):

```
[Docente] → sube PDF → [Extracción + Chunking] → [Embeddings Vertex AI]
                                                          ↓
                                                  [Firestore chunks]
                                                          ↑
[Estudiante] → pregunta → [Reescritura] → [Embedding] → [Top-k coseno]
                                                          ↓
                              [Ensamblaje prompt: modo + historial + chunks]
                                                          ↓
                                              [Gemini 2.5 Flash]
                                                          ↓
                                              [Respuesta con cita 📄]
```

**3 pasos a destacar verbalmente:**
1. **Ingesta**: el docente sube el material y se vectoriza una vez.
2. **Retrieval**: cada pregunta busca los fragmentos más parecidos por similitud coseno.
3. **Generación**: Gemini responde SOLO con esos fragmentos y cita la fuente.

**Notas:** "Este es el slide más técnico, le dedico 90 segundos. La arquitectura tiene dos pipelines: ingesta (izquierda) y conversación (derecha). El docente sube material UNA vez; el sistema lo trocea en fragmentos, los convierte en vectores y los guarda. Cuando un estudiante pregunta, su consulta también se vectoriza, se buscan los fragmentos más parecidos por coseno, y Gemini responde usando SOLO ese contexto. Esto garantiza que la respuesta venga del material, no de internet, y por eso podemos citar `[📄 doc, página X]`."

---

## SLIDE 6 — Stack tecnológico (60s)

**Título:** Stack y justificación

| Capa | Tecnología | Por qué |
|---|---|---|
| Frontend | React 19 + Vite | Estándar industria, hot-reload rápido |
| Backend | Python 3.11 + FastAPI | Async nativo, OpenAPI auto |
| LLM | Gemini 2.5 Flash | Cuota gratuita Vertex AI + bajo costo |
| Embeddings | text-embedding-004 | 768 dims, mismo proveedor (latencia) |
| BD operativa | Firestore | NoSQL serverless, escala automática |
| BD vectorial | BigQuery Vector Search | Escalable, SQL conocido |
| Auth | Firebase Auth + Google | Restricción dominio @tecsup |
| Despliegue | Cloud Run (contenedores) | Pay-per-use, escala a 0 |

**Notas:** "Stack 100% GCP por consistencia, latencia (mismo data center) y porque la cuota académica de Google Cloud cubre el proyecto sin costo. Gemini Flash en vez de Pro porque la diferencia de calidad para RAG es marginal y el costo es 10× menor."

---

## SLIDE 7 — Cronograma / Gantt (45s)

**Título:** 9 sprints de 2 semanas

**Visual:** Gantt horizontal con los 9 sprints. Resaltar:
- 🟦 Sprint 0–4: MVP (hito 50%)
- 🟩 Sprint 5–8: Funcionalidades avanzadas (hito 100%)
- 🟨 Sprint 9: Escalabilidad RAG

| Sprint | Objetivo | Hito |
|---|---|---|
| 0 | Setup + deploy hello world | ✅ |
| 1 | Auth + roles + CRUD cursos | ✅ |
| 2 | Ingesta + embeddings | ✅ |
| 3 | RAG + chat | ✅ |
| 4 | Frontend integrado | **50%** ✅ |
| 5 | Modo socrático | ✅ |
| 6 | Quizzes | ✅ |
| 7 | Analítica + feedback | ✅ |
| 8 | Hardening + tests | **100%** ✅ |
| 9 | BigQuery Vector Search | ✅ |

**Notas:** "9 sprints de 2 semanas. El MVP llegó al 50% en sprint 4 con la demo end-to-end. El 100% se cumplió en sprint 8 con tests y hardening. El sprint 9 fue valor agregado para escalabilidad."

---

## SLIDE 8 — Impacto académico (60s)

**Título:** Contribución pedagógica

**Bullets:**
- **Diferenciador**: modo Socrático que enseña a razonar, no solo a copiar respuestas.
- **Trazabilidad**: cada respuesta cita la página exacta del material institucional.
- **Replicable**: arquitectura aplicable a cualquier carrera/curso con material digitalizado.
- **Línea futura**: estudio cuasi-experimental — grupo control vs grupo con ProfeTEC para medir mejora en notas.
- **Apertura**: código liberado bajo licencia académica.

**Visual:** Captura comparativa de la misma pregunta en modo Directo vs Socrático.

**Notas:** "El valor no es solo técnico. ProfeTEC contribuye al estado del arte porque la mayoría de tutores IA actuales solo dan la respuesta. El modo socrático fuerza al estudiante a razonar — esto está alineado con la pedagogía constructivista. Es replicable a cualquier carrera y deja preparado un estudio futuro con grupo control."

---

## SLIDE 9 — Resultados (60s)

**Título:** Resultados verificables

**Bullets:**
- ✅ **Despliegue productivo** en Cloud Run (URL pública).
- ✅ **37+ tests automatizados** pasando (`pytest -q`).
- ✅ **Pipeline RAG completo**: ingesta → retrieval → generación con citas.
- ✅ **Modo dual operativo**: A/B comparable desde el toggle del frontend.
- ✅ **Analítica funcional**: mensajes/modo, feedback +/−, aciertos quiz.
- ✅ **2 backends RAG**: firestore_scan (local) + bigquery_vector (escala).

**Visual:** 3 screenshots en mosaico:
1. Chat funcionando con cita.
2. Panel de analítica del docente.
3. Resultado de `pytest` con tests pasando.

**Notas:** "Resultados concretos: producto desplegado, 37 tests automáticos pasando, ambos modos pedagógicos operativos, analítica funcional. Todo verificable en vivo en la demo."

---

## SLIDE 10 — Conclusiones (45s)

**Título:** Conclusiones

**Bullets:**
1. **Es viable** construir un tutor RAG sobre Gemini con cuota gratuita académica, sin costos prohibitivos.
2. **El modo socrático es factible técnicamente** con un solo modelo y dos `system_instruction` — no requiere modelos distintos.
3. **La calidad depende del material**: garbage in → garbage out. La restricción a fuentes del docente es una ventaja, no una limitación.

**Notas:** "Tres conclusiones: la viabilidad económica con cuota académica, la simplicidad técnica del modo dual (un solo modelo, dos prompts), y que la calidad del tutor depende directamente del material que sube el docente."

---

## SLIDE 11 — Recomendaciones / trabajo futuro (30s)

**Título:** Trabajo futuro

**Bullets:**
- **Multimodal**: soportar imágenes, diagramas, código.
- **Migrar a Vector Search gestionado** (Vertex AI Vector Search).
- **Estudio con grupo control** para medir impacto en notas.
- **Integración LMS** (Moodle/Canvas) vía LTI.
- **Voz**: tutor por audio para accesibilidad.

**Notas:** "Cinco líneas de continuidad. La más interesante académicamente es el estudio con grupo control para medir el impacto real en aprendizaje."

---

## SLIDE 12 — Cierre (10s)

**Título grande:** Gracias

**Bullets:**
- Repositorio: `github.com/[tu-usuario]/ProfeTEC`
- Demo: `[URL Cloud Run]`
- Contacto: helpdesk@comutelperu.com

**Notas:** "Gracias. Quedo atento a preguntas."

---

# SLIDES OCULTOS DE RESPALDO (al final del PPT, no se muestran salvo pregunta)

Estos los saltas SOLO si el jurado pregunta. Numéralos desde el #13 en adelante.

## SLIDE 13 (oculto) — Diagrama de Ishikawa

**Cuándo mostrarlo:** Si preguntan "¿cuáles son las causas raíz del problema?"

**Estructura del fishbone — efecto:** _"Estudiantes no resuelven dudas fuera del aula"_

5 ramas (espinas):
1. **Docente** — Tiempo limitado · Atiende a 30+ estudiantes · No tiene canal asincrónico
2. **Material** — Disperso (Drive, PDFs, PPTs) · No indexado · Difícil de buscar
3. **Método** — Tutorías solo presenciales · Sin pedagogía socrática asistida
4. **Canal** — WhatsApp informal · Sin trazabilidad · Sin contexto del curso
5. **Herramientas** — Chatbots genéricos no conocen el material · No citan fuentes

---

## SLIDE 14 (oculto) — Modelo DER (Firestore)

**Cuándo mostrarlo:** Si preguntan "¿cuál es el modelo de datos?"

**Colecciones y relaciones clave:**

```
usuarios (1) ──── (N) matriculas (N) ──── (1) cursos
                                                │
                                                ├── (1:N) documentos ──── (1:N) chunks
                                                │
                                                ├── (1:N) conversaciones ──── (1:N) mensajes
                                                │
                                                └── (1:N) quizzes ──── (1:N) quiz_intentos
```

**9 colecciones:**
- `usuarios/{uid}` — rol, email, nombre
- `docentes_autorizados/{email}` — whitelist
- `cursos/{curso_id}` — título, código, docente_id
- `matriculas/{curso_id}_{uid}` — N:N alumno-curso
- `documentos/{doc_id}` — nombre, URL Cloud Storage, estado
- `chunks/{chunk_id}` — texto, embedding[768], curso_id, pagina
- `conversaciones/{conv_id}` — curso_id, usuario_id
- `mensajes/{msg_id}` — rol, texto, modo, chunks_citados, feedback
- `quizzes/{quiz_id}` + `quiz_intentos/{intento_id}`

---

## SLIDE 15 (oculto) — Tabla de evaluación de herramientas

**Cuándo mostrarlo:** Si preguntan "¿por qué elegiste X y no Y?"

| Decisión | Opción elegida | Alternativa | Criterio determinante |
|---|---|---|---|
| **LLM** | Gemini 2.5 Flash | GPT-4 / Claude | Cuota académica GCP gratuita + 10× más barato que Pro |
| **BD operativa** | Firestore | PostgreSQL + pgvector | Serverless, sin mantenimiento, integración nativa con Firebase Auth |
| **BD vectorial** | BigQuery Vector Search | Pinecone / Weaviate | Sin costo extra (ya pagamos GCP), SQL conocido |
| **Backend** | FastAPI | Django / Flask | Async nativo, OpenAPI auto, ideal para streaming SSE |
| **Despliegue** | Cloud Run | App Engine / GKE | Pay-per-use, escala a 0, contenedor genérico |
| **Auth** | Firebase Auth | Auth0 / Keycloak | Gratis hasta 50k MAU, integración Google nativa |

---

## SLIDE 16 (oculto) — Diagrama de casos de uso

**Cuándo mostrarlo:** Si preguntan por casos de uso detallados.

**Actores:** 🎓 Docente · 👤 Estudiante

**Casos de uso del Docente:**
- Crear/editar curso
- Subir material académico
- Crear quiz desde material
- Consultar analítica del curso
- Gestionar matrículas

**Casos de uso del Estudiante:**
- Matricularse en curso (con código)
- Conversar con el tutor (modo Directo)
- Conversar con el tutor (modo Socrático)
- Dar feedback 👍/👎
- Resolver quiz

**Casos de uso compartidos:** Login con Google, ver historial.

---

## SLIDE 17 (oculto) — BPMN del proceso completo

**Cuándo mostrarlo:** Si preguntan por el flujo de negocio.

**Visual:** El PNG `Procesos ProfeTEC.png` que ya tienes, o el Mermaid de `bpmn-proceso.md` (diagrama completo con 3 carriles: Docente / Alumno / Sistema).

**3 sub-procesos a mencionar:**
1. **Ingesta** (Docente → Sistema)
2. **Chat RAG** (Alumno → Sistema, con bifurcación Directo/Socrático)
3. **Analítica** (Docente → Sistema)

---

## SLIDE 18 (oculto) — Detalle modo Socrático

**Cuándo mostrarlo:** Si preguntan "¿cómo decide el modo socrático cuándo dar la respuesta?"

**3 condiciones de salida** (cualquiera dispara la síntesis final):
1. El estudiante ya razonó lo esencial.
2. El estudiante se rinde explícitamente ("no lo sé", "ayúdame").
3. Lleva varios intentos sin avanzar.

**Detalle técnico:** Un solo modelo Gemini, dos `system_instruction` distintos (`SYSTEM_PROMPT_DIRECTO` y `SYSTEM_PROMPT_SOCRATICO`).

---

## SLIDE 19 (oculto) — Pantallazos adicionales

Tener listos:
- Login con Google + onboarding
- Carga de PDF + visualización de chunks
- Chat en modo Directo con cita visible
- Chat en modo Socrático con pista
- Quiz generado por IA + corrección
- Panel de analítica con métricas por modo

---

# Cheat sheet de la sustentación

## Si te preguntan…

| Pregunta probable | Slide al que saltas | Respuesta corta |
|---|---|---|
| ¿Por qué Gemini y no GPT-4? | #15 | "Cuota académica GCP gratuita + integración con Vertex" |
| ¿Cómo está modelada la BD? | #14 | "9 colecciones en Firestore, relaciones por foreign key" |
| ¿Cuál es la causa raíz? | #13 | "Tutoría 1-a-1 no escala — 5 causas en Ishikawa" |
| ¿Casos de uso? | #16 | "2 actores, ~10 casos de uso" |
| ¿Modelo de negocio? | — | "Diseñado como contribución académica abierta; viabilidad económica como trabajo futuro" |
| ¿Qué pasa si el material es malo? | #10 | "Garbage in, garbage out — pero la restricción al material es una ventaja, no limitación" |
| ¿Cómo evitas alucinaciones? | #5 | "Grounding check: si la respuesta no contiene cita y hay chunks sólidos, se reintenta. Si no hay material, lo declara." |
| ¿Cuántos usuarios soporta? | #6 | "Cloud Run escala automático; BigQuery Vector maneja millones de chunks" |
| ¿Hiciste pruebas con usuarios? | #11 | "Piloto interno; estudio con grupo control queda como trabajo futuro" |

## Datos numéricos a memorizar

- **9** sprints de 2 semanas = ~18 semanas de desarrollo.
- **25** requerimientos funcionales en **5** épicas.
- **37+** tests automatizados pasando.
- **768** dimensiones del vector de embedding.
- **6** turnos de memoria conversacional inyectados al prompt.
- **2** modos pedagógicos (Directo / Socrático).
- **2** backends RAG (firestore_scan / bigquery_vector).
