```mermaid
flowchart TD
    %% ══════════════════ ACTORES ══════════════════
    DOCENTE(["🎓 Docente"])
    ESTUDIANTE(["👤 Estudiante"])

    %% ══════════════ PIPELINE DE INGESTA ══════════════
    subgraph INGESTA["PIPELINE DE INGESTA  (iniciado por Docente)"]
        direction LR
        PDF["Documentos académicos\nPDF / PPTX"]
        PROC["Paso 1 — Extracción de texto\n+ Chunking por páginas"]
        VEC["Paso 2 — Vectorización\nVertex AI text-embedding-004\n768 dimensiones"]
        GCS[("Google Cloud Storage\nPDFs originales  gs://")]
        FS_CHUNKS[("Firestore — colección 'chunks'\ntexto + embedding + metadata")]

        PDF --> PROC --> VEC --> FS_CHUNKS
        PROC -.->|archivo original| GCS
    end

    %% ══════════════ PIPELINE DE CONVERSACIÓN ══════════════
    subgraph CONV["PIPELINE DE CONVERSACIÓN  (Estudiante)"]
        direction TB
        PREGUNTA["Pregunta del estudiante"]
        REWRITE["Paso 3 — Reescritura de consulta\nreescribir_consulta()\nContextualiza seguimientos cortos\n('no lo sé', '¿y eso?') con el historial\nSe omite si la pregunta ya es autónoma"]
        QEMBED["Paso 4 — Embedding de la consulta reescrita\ntext-embedding-004"]
        ASSEMBLY["Paso 5 — Ensamblaje del prompt\n• Fragmentos RAG recuperados\n• Historial conversacional (últimos turnos)\n• Modo pedagógico (Directo / Socrático)\n• Flag rendicion → fuerza síntesis\n• Flag contexto_debil → avisa al modelo"]
        LLM["LLM — GEMINI 2.5 FLASH\nvía Vertex AI"]
        RESPUESTA["Respuesta pedagógica\nstreaming SSE → cliente React"]
    end

    %% ══════════════ PIPELINE DE QUIZZES ══════════════
    subgraph QUIZ["PIPELINE DE QUIZZES"]
        direction LR
        QGEN["Generador de quiz\nquiz_generator.py + Gemini\npreguntas desde el material del curso"]
        FS_QUIZ[("Firestore\n'quizzes' / 'quiz_intentos'")]
        QGEN --> FS_QUIZ
    end

    %% ══════════════ ANALÍTICA ══════════════
    subgraph ANALYTICS["ANALÍTICA DEL DOCENTE"]
        ANALY["Endpoint /analytics\nmensajes · feedback · quizzes\nmatrículas · chunks · aciertos"]
    end

    %% ══════════════ SERVICIOS TRANSVERSALES ══════════════
    subgraph SVC["SERVICIOS TRANSVERSALES"]
        direction LR
        AUTH["Firebase Authentication\nlogin Google — dominio restringido"]
        FS_CONV[("Firestore\n'conversaciones' / 'mensajes'")]
        DB[("Firestore\ncursos · usuarios · matrículas\ndocumentos · feedback")]
        APP["Backend FastAPI\n+ Frontend React / Vite"]
        BQ["(Opcional)\nBigQuery Vector Search"]
    end

    %% ── Docente ──────────────────────────────────────
    DOCENTE -->|"sube documentos"| PDF
    DOCENTE -->|"crea quiz"| QGEN
    DOCENTE -->|"consulta métricas"| ANALY
    DOCENTE -.->|autenticación| AUTH

    %% ── Estudiante ───────────────────────────────────
    ESTUDIANTE -->|"envía pregunta"| PREGUNTA
    RESPUESTA -->|"recibe respuesta"| ESTUDIANTE
    ESTUDIANTE -->|"responde quiz"| FS_QUIZ
    ESTUDIANTE -.->|autenticación| AUTH

    %% ── RAG: búsqueda semántica ───────────────────────
    QEMBED -->|"similitud coseno  top-k\n+ fallback al turno anterior si vacío"| FS_CHUNKS
    FS_CHUNKS -->|"fragmentos relevantes"| ASSEMBLY

    %% ── Memoria conversacional ────────────────────────
    FS_CONV -->|"historial → contexto\npara reescritura"| REWRITE
    FS_CONV -->|"historial → memoria\ndel diálogo"| ASSEMBLY

    %% ── Persistencia de respuesta ────────────────────
    LLM -.->|"guarda respuesta\n+ chunks citados"| FS_CONV

    %% ── Analítica ────────────────────────────────────
    FS_CONV -->|"mensajes + feedback"| ANALY
    FS_QUIZ -->|"intentos + aciertos"| ANALY

    %% ── Backend alterno BigQuery ──────────────────────
    FS_CHUNKS -.->|"replica vectores"| BQ
    BQ -.->|"búsqueda alternativa"| ASSEMBLY

    %% ══════════════ ESTILOS ══════════════
    classDef actor   fill:#0f172a,stroke:#334155,stroke-width:1.5px,color:#f8fafc;
    classDef store   fill:#dbeafe,stroke:#3b82f6,stroke-width:1px,color:#0f172a;
    classDef proc    fill:#eff6ff,stroke:#60a5fa,stroke-width:1px,color:#0f172a;
    classDef model   fill:#1d4ed8,stroke:#1e3a8a,stroke-width:1px,color:#ffffff;
    classDef ext     fill:#f1f5f9,stroke:#94a3b8,stroke-width:1px,color:#0f172a;
    classDef new     fill:#fef3c7,stroke:#f59e0b,stroke-width:2px,color:#0f172a;

    class DOCENTE,ESTUDIANTE actor;
    class FS_CHUNKS,GCS,FS_CONV,DB,FS_QUIZ store;
    class PROC,VEC,QEMBED,ASSEMBLY,QGEN,ANALY proc;
    class LLM model;
    class BQ,AUTH,APP,PDF,PREGUNTA,RESPUESTA ext;
    class REWRITE new;
```

## Actores

| Actor | Rol en el sistema |
|---|---|
| **Docente** | Sube documentos (dispara ingesta), crea quizzes, consulta analítica del curso |
| **Estudiante** | Conversa con el tutor RAG (modo Directo o Socrático), responde quizzes |

## Notas de fidelidad al código

### Pipeline de ingesta
- Soporta **PDF** (`pypdf`) y **PPTX** (`python-pptx`) — [documentos.py](../backend/app/routers/documentos.py).
- Chunking por páginas; cada chunk guarda `texto + embedding + nombre_doc + pagina + curso_id`.
- Backend de recuperación configurable: `firestore_scan` (default, coseno en Python) o `bigquery_vector` — `settings.rag_backend`.

### Pipeline de conversación
- **Paso 3 — Reescritura de consulta** ⭐ nuevo: `reescribir_consulta()` en [gemini.py](../backend/app/core/gemini.py).
  - Se omite si el mensaje ya tiene ≥6 palabras y no contiene términos vagos (`_necesita_reescritura`).
  - Se omite si no hay historial (primer mensaje de la conversación).
- **Flag `rendicion`**: activo cuando el estudiante dice "no lo sé" / "ayúdame" en modo socrático → obliga síntesis final.
- **Flag `contexto_debil`**: activo cuando el mejor score RAG < `rag_score_confianza` (0.6) → avisa al modelo que el contexto es parcial.
- **Fallback de chunks**: si la búsqueda devuelve vacío en una conversación existente, se reutilizan los `chunks_usados` del turno anterior.
- **Grounding check**: si la respuesta no contiene `[📄…]` con chunks sólidos disponibles, se reintenta con instrucción explícita de citar.
- **Robustez streaming**: si el stream termina vacío o con `MAX_TOKENS`, cae al endpoint síncrono y emite el resultado completo.

### Pipeline de quizzes
- `quiz_generator.py` llama a Gemini para generar preguntas desde los chunks del curso.
- Los intentos se guardan en `quiz_intentos` con `correctas / total_preguntas`.

### Analítica del docente
- Endpoint `GET /cursos/{id}/analytics` — solo accesible para el docente dueño del curso.
- Agrega: mensajes por modo, feedback positivo/negativo, aciertos de quizzes, total de chunks indexados.

### Embeddings y LLM
- **Embeddings:** Vertex AI `text-embedding-004` (768 dimensiones) — [vertex.py](../backend/app/core/vertex.py).
- **LLM:** Gemini 2.5 Flash vía Vertex AI — [gemini.py](../backend/app/core/gemini.py).
- **Memoria conversacional:** últimos 6 turnos inyectados en el prompt (`HISTORIAL_MAX_TURNOS`).
- **Modo pedagógico:** Directo vs Socrático = dos `system_instruction` distintos en `GenerativeModel`.
- **Auth:** Firebase Authentication con dominio de email restringido (`allowed_email_domains`).
