## Arquitectura del Proyecto

## Docente

Sube documentos (dispara ingesta), crea quizzes, consulta analítica del curso

```mermaid
flowchart TB
    DOCENTE(["🎓 Docente"])

    %% Ingesta
    subgraph INGESTA["📘 PIPELINE DE INGESTA"]
        direction LR
        s13["📄 PDF / PPTX"]
        s14["⚙️ Procesamiento (extracción + chunking)"]
        s15["🔢 Vectorización<br>Vertex AI embedding"]
        s31["☁️ GCS (PDFs originales)"]
        s32["💾 Firestore — 'chunks' (texto + embeddings + metadata)"]

        DOCENTE -->|"📤 Sube documentos"| s13
        s13 --> s14 --> s15 --> s32
        s14 -.->|"Copia original"| s31
    end

    %% Quizzes
    subgraph QUIZ["🧠 PIPELINE DE QUIZZES"]
        direction LR
        s24["🧩 Generador de quiz<br>(Gemini / IA)"]
        s33["💾 Firestore — quizzes / intentos"]
        DOCENTE -->|"📝 Crea quiz"| s24 --> s33
    end

    %% Analítica
    subgraph ANALYTICS["📊 ANALÍTICA DEL DOCENTE"]
        s26["📈 /analytics — métricas de uso y desempeño"]
        DOCENTE -->|"📈 Consulta métricas"| s26
    end

    %% Servicios comunes
    subgraph SVC["⚙️ SERVICIOS TRANSVERSALES"]
        s28["🔐 Firebase Auth"]
        s29["💻 FastAPI + React/Vite"]
        s34["💾 Firestore — conversaciones / mensajes"]
        s35["📚 Firestore — cursos, usuarios, documentos, feedback"]
        s30["🧮 BigQuery Vector Search"]
        s28 --> s29 --> s35
        s34 -.->|"Datos para analítica"| s26
    end

    %% Conexiones extra
    s33 -->|"📊 Resultados de quizzes"| s26
    s32 -.->|"Vectores (réplica)"| s30 -.->|"Búsqueda alternativa"| s26

    %% Estilos
    classDef actor fill:#1e293b,stroke:#334155,stroke-width:1.5px,color:#f8fafc;
    classDef store fill:#e0f2fe,stroke:#0284c7,color:#082f49,stroke-width:1px;
    classDef proc fill:#eef2ff,stroke:#6366f1,color:#1e1b4b,stroke-width:1px;
    class DOCENTE actor;
    class s13,s31,s32,s33,s34,s35 store;
    class s14,s15,s24,s26,s29,s30 proc;
    class s28 ext;
```

## Estudiante 

Conversa con el tutor RAG (modo Directo o Socrático), responde quizzes


```mermaid
flowchart TB
    ESTUDIANTE(["👤 Estudiante"])

    %% Conversación
    subgraph CONV["💬 PIPELINE DE CONVERSACIÓN"]
        direction TB
        s17["❓ Pregunta del estudiante"]
        s18["🪄 Reescritura contextual"]
        s19["🔢 Embedding de consulta<br>Vertex AI embedding"]
        s20["🧩 Ensamblaje del prompt<br>(fragmentos + historial + modo pedagógico)"]
        s21["🤖 Gemini 2.5 Flash"]
        s22["💡 Respuesta pedagógica<br>(streaming SSE)"]
        s32["💾 Firestore — 'chunks'<br>(conocimiento base)"]
        s34["💾 Firestore — 'conversaciones' / 'mensajes'"]

        ESTUDIANTE -->|"💬 Envía pregunta"| s17
        s17 --> s18 --> s19 --> s20 --> s21 --> s22 -->|"📥 Recibe respuesta"| ESTUDIANTE

        %% Recuperación de contexto
        s19 -->|"🔍 Similitud coseno (top‑k)"| s32 -->|"📚 Fragmentos relevantes"| s20
        s34 -->|"🧠 Historial de diálogo"| s20
        s34 -->|"↪ Contexto para reescritura"| s18
        s21 -.->|"💾 Guarda respuesta + citas"| s34
    end

    %% Quizzes
    subgraph QUIZ["🧠 PIPELINE DE QUIZZES"]
        direction LR
        s33["💾 Firestore — quizzes / intentos"]
        ESTUDIANTE -->|"✅ Responde quiz"| s33
    end

    %% Servicios comunes
    subgraph SVC["⚙️ SERVICIOS TRANSVERSALES"]
        s28["🔐 Firebase Auth"]
        s29["💻 Frontend React/Vite + Backend FastAPI"]
        s35["📚 Firestore — cursos, usuarios, documentos, feedback"]
        s28 --> s29 --> s35
    end

    %% Analítica (indirecta)
    s33 -->|"📊 Aciertos y participación"| s35
    s34 -->|"Mensajes y feedback"| s35

    %% Estilos
    classDef actor fill:#1e293b,stroke:#334155,stroke-width:1.5px,color:#f8fafc;
    classDef store fill:#e0f2fe,stroke:#0284c7,color:#082f49,stroke-width:1px;
    classDef proc fill:#eef2ff,stroke:#6366f1,color:#1e1b4b,stroke-width:1px;
    class ESTUDIANTE actor;
    class s32,s33,s34,s35 store;
    class s18,s19,s20,s21,s22,s29 proc;
    class s28 ext;
```




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
