# Proceso de negocio — ProfeTEC.IA (BPMN)

Guía para reconstruir el diagrama BPMN en Bizagi, alineado con el sistema
realmente implementado: tutor de **chat conversacional RAG** sobre documentos del
curso, con modos Directo/Socrático, quizzes y panel de analítica para el docente.

> Reemplaza al diagrama antiguo basado en "ejercicios", que describía un producto
> distinto y tenía las salidas de autenticación invertidas.

## Estructura

**Pool:** `Proceso de ProfeTEC.IA`
**Carriles (lanes):**
1. **Docente**
2. **Alumno**
3. **Sistema (IA + RAG)**

Tipos de elemento: *evento* (inicio/fin), *tarea usuario* (acción de persona),
*tarea servicio* (acción automática del sistema), *compuerta XOR* (decisión
exclusiva), *compuerta AND* (paralelo).

---

## A) Autenticación

| Elemento | Tipo | Carril |
|---|---|---|
| Inicio | Evento inicio | Alumno |
| ¿Tiene cuenta? | Compuerta XOR | Alumno |
| Iniciar sesión con Google | Tarea usuario | Alumno |
| Registrarse (Onboarding) | Tarea usuario | Alumno |
| Validar dominio @tecsup.edu.pe | Tarea servicio | Sistema |
| Mostrar pantalla principal | Tarea servicio | Sistema |

**Flujos:**
- Inicio → ¿Tiene cuenta?
- ¿Tiene cuenta? → **Sí** → Iniciar sesión con Google
- ¿Tiene cuenta? → **No** → Registrarse (Onboarding)
- Ambas → Validar dominio @tecsup.edu.pe → Mostrar pantalla principal → ¿Qué rol?

> Nota: el login real es Google OAuth con dominio restringido (Firebase Auth),
> no un "crear cuenta / iniciar sesión" con usuario y contraseña.

---

## B) Ingesta de documentos (Docente)

| Elemento | Tipo | Carril |
|---|---|---|
| ¿Qué rol? | Compuerta XOR | Sistema |
| Subir documento (PDF/PPTX) | Tarea usuario | Docente |
| Extraer texto + Chunking por páginas | Tarea servicio | Sistema |
| Generar embeddings (text-embedding-004) | Tarea servicio | Sistema |
| Guardar chunks en Firestore | Tarea servicio | Sistema |
| Guardar PDF original en Cloud Storage | Tarea servicio | Sistema |
| Documento listo para consultas | Evento fin | Sistema |

**Flujos:**
- ¿Qué rol? → **Docente** → Subir documento
- Subir documento → Extraer texto + Chunking → **(compuerta AND)**
- AND → Generar embeddings → Guardar chunks en Firestore → Documento listo
- AND → Guardar PDF original en Cloud Storage

---

## C) Conversación / Chat RAG (Alumno) — núcleo del sistema

| Elemento | Tipo | Carril |
|---|---|---|
| ¿Qué desea hacer? | Compuerta XOR | Alumno |
| Escribir pregunta | Tarea usuario | Alumno |
| Elegir modo (Directo / Socrático) | Tarea usuario | Alumno |
| ¿Hay historial y pregunta ambigua? | Compuerta XOR | Sistema |
| Reescribir consulta con historial | Tarea servicio | Sistema |
| Generar embedding de la consulta | Tarea servicio | Sistema |
| Buscar fragmentos relevantes (top-k, coseno) | Tarea servicio | Sistema |
| ¿Encontró material? | Compuerta XOR | Sistema |
| Reusar fragmentos del turno anterior | Tarea servicio | Sistema |
| Ensamblar prompt (contexto + modo + historial) | Tarea servicio | Sistema |
| Generar respuesta con Gemini 2.5 Flash | Tarea servicio | Sistema |
| Mostrar respuesta con citas (streaming) | Tarea servicio | Sistema |
| Dar feedback 👍/👎 | Tarea usuario | Alumno |
| Guardar mensaje y citas en Firestore | Tarea servicio | Sistema |
| ¿Otra pregunta? | Compuerta XOR | Alumno |
| Fin conversación | Evento fin | Alumno |

**Flujos:**
- ¿Qué rol? → **Alumno** → ¿Qué desea hacer? → **Conversar** → Escribir pregunta
- Escribir pregunta → Elegir modo → ¿Hay historial y pregunta ambigua?
- ¿Hay historial...? → **Sí** → Reescribir consulta → Generar embedding
- ¿Hay historial...? → **No** → Generar embedding *(salta la reescritura)*
- Generar embedding → Buscar fragmentos relevantes → ¿Encontró material?
- ¿Encontró material? → **No (y hay historial)** → Reusar fragmentos del turno anterior → Ensamblar prompt
- ¿Encontró material? → **Sí** → Ensamblar prompt
- Ensamblar prompt → Generar respuesta con Gemini → Mostrar respuesta con citas → Dar feedback
- Dar feedback → Guardar mensaje y citas → ¿Otra pregunta?
- ¿Otra pregunta? → **Sí** → Escribir pregunta *(bucle)*
- ¿Otra pregunta? → **No** → Fin conversación

> Detalles que el ensamblaje del prompt aplica internamente:
> - **Modo pedagógico**: Directo (responde) vs Socrático (guía con preguntas).
> - **Flag rendición**: si el alumno dice "no lo sé"/"ayúdame" en modo socrático,
>   se fuerza la síntesis final.
> - **Flag contexto débil**: si el mejor score de similitud es bajo, se avisa al
>   modelo para que no complete con conocimiento externo.

---

## C.1) Bifurcación por modo pedagógico (Directo vs Socrático)

Tras *Ensamblar prompt*, la tarea *Generar respuesta con Gemini* se comporta
distinto según el modo que eligió el alumno. Esto se controla con dos
`system_instruction` diferentes (no son dos modelos distintos), pero a nivel de
proceso conviene representarlo como una compuerta.

| Elemento | Tipo | Carril |
|---|---|---|
| ¿Modo pedagógico? | Compuerta XOR | Sistema |
| Generar respuesta directa con citas | Tarea servicio | Sistema |
| ¿Rendición o ya razonó lo esencial? | Compuerta XOR | Sistema |
| Generar síntesis final con citas | Tarea servicio | Sistema |
| Generar pista / pregunta guía (sin citas) | Tarea servicio | Sistema |

**Flujos:**
- Ensamblar prompt → ¿Modo pedagógico?
- ¿Modo pedagógico? → **Directo** → Generar respuesta directa con citas → Mostrar respuesta
- ¿Modo pedagógico? → **Socrático** → ¿Rendición o ya razonó lo esencial?
- ¿Rendición...? → **Sí** → Generar síntesis final con citas → Mostrar respuesta
- ¿Rendición...? → **No** → Generar pista / pregunta guía (sin citas) → Mostrar respuesta

### Cómo funciona cada modo

**Modo Directo** (`SYSTEM_PROMPT_DIRECTO`):
1. Responde de inmediato, sin saludo, empezando por la respuesta.
2. Usa únicamente el material recuperado y **cita siempre** la fuente `[📄 doc, pág. X]`.
3. Es de un solo turno: pregunta → respuesta completa.

**Modo Socrático** (`SYSTEM_PROMPT_SOCRATICO`):
1. **No** entrega la solución de entrada: arranca con una pista breve o una
   pregunta guía basada en el material.
2. Avanza en pasos pequeños; según lo que responde el alumno ajusta la siguiente
   pista (máximo 2-3 preguntas por turno).
3. Reconoce los aciertos previos y no repite preguntas ya contestadas
   (usa la memoria conversacional).
4. **Cita solo** cuando afirma contenido del material o da la síntesis final;
   no cita cuando su turno es solo una pregunta guía.
5. **Condición de salida** → da la síntesis final con cita cuando:
   - el alumno ya razonó lo esencial, **o**
   - pide explícitamente la respuesta / se rinde ("no lo sé", "ayúdame"), **o**
   - lleva varios intentos sin avanzar.

> Es decir: el modo Directo termina en un turno; el Socrático es un **bucle de
> guía** (pista → respuesta del alumno → siguiente pista) que se cierra con la
> síntesis cuando se cumple la condición de salida.

### Diagrama del modo (Mermaid)

```mermaid
flowchart TD
    ENS[Ensamblar prompt] --> MODO{¿Modo pedagógico?}

    MODO -->|Directo| DIR[Generar respuesta directa con citas]
    DIR --> SHOW[Mostrar respuesta con citas]

    MODO -->|Socrático| COND{¿Rendición o ya\nrazonó lo esencial?}
    COND -->|No| GUIA[Generar pista / pregunta guía\nsin citas]
    GUIA --> SHOW
    COND -->|Sí| SINT[Generar síntesis final con citas]
    SINT --> SHOW

    SHOW --> FB[Dar feedback 👍/👎]
    FB --> Q5{¿Otra pregunta?}
    Q5 -->|Sí, en socrático| COND2[El alumno responde la pista\n→ nuevo turno]
    Q5 -->|No| FIN((Fin))
```

---

## D) Quizzes

| Elemento | Tipo | Carril |
|---|---|---|
| Crear quiz (rango de semanas) | Tarea usuario | Docente |
| Generar preguntas con IA desde el material | Tarea servicio | Sistema |
| Responder quiz | Tarea usuario | Alumno |
| Calificar y guardar intento | Tarea servicio | Sistema |

**Flujos:**
- ¿Qué desea hacer? → **Practicar** → Responder quiz → Calificar y guardar intento → ¿Otra actividad?
- (Lado docente) Crear quiz → Generar preguntas con IA → *(quiz disponible para alumnos)*

---

## E) Analítica del docente

| Elemento | Tipo | Carril |
|---|---|---|
| Consultar analítica del curso | Tarea usuario | Docente |
| Agregar métricas (mensajes, feedback, aciertos) | Tarea servicio | Sistema |
| Mostrar panel | Tarea servicio | Sistema |

**Flujos:**
- ¿Qué rol? → **Docente** → Consultar analítica → Agregar métricas → Mostrar panel → Fin

---

## Diagrama de referencia (Mermaid)

```mermaid
flowchart LR
    subgraph AL[Alumno]
        I((Inicio)) --> Q1{¿Tiene cuenta?}
        Q1 -->|Si| LOGIN[Iniciar sesion Google]
        Q1 -->|No| REG[Registrarse / Onboarding]
        PREG[Escribir pregunta] --> MODO[Elegir modo D/S]
        FB[Dar feedback] --> Q5{¿Otra pregunta?}
        Q5 -->|Si| PREG
        Q5 -->|No| FIN((Fin))
    end
    subgraph DOC[Docente]
        SUB[Subir documento]
        CQ[Crear quiz]
        ANA[Consultar analitica]
    end
    subgraph SIS["Sistema (IA + RAG)"]
        LOGIN --> VAL[Validar dominio]
        REG --> VAL
        VAL --> HOME[Pantalla principal] --> ROL{¿Que rol?}
        ROL -->|Docente| SUB
        ROL -->|Alumno| QDES{¿Que desea?}
        QDES -->|Conversar| PREG
        SUB --> CHUNK[Extraer texto + chunking] --> EMB1[Embeddings] --> SAVE[(Guardar chunks Firestore)]
        MODO --> Q2{¿Historial y ambigua?}
        Q2 -->|Si| REW[Reescribir consulta] --> EMB2[Embedding consulta]
        Q2 -->|No| EMB2
        EMB2 --> BUS[Buscar top-k coseno] --> Q3{¿Encontro material?}
        Q3 -->|No| REUSE[Reusar turno anterior] --> ENS[Ensamblar prompt]
        Q3 -->|Si| ENS
        ENS --> MODO2{¿Modo?}
        MODO2 -->|Directo| DIR[Respuesta directa con citas]
        MODO2 -->|Socratico| SOC{¿Rendicion o ya razono?}
        SOC -->|No| GUIA[Pista / pregunta guia]
        SOC -->|Si| SINT[Sintesis final con citas]
        DIR --> RESP[Mostrar respuesta]
        GUIA --> RESP
        SINT --> RESP
        RESP --> FB
    end
```

## Diagrama completo (Mermaid) — todo el proceso

Integra los 5 sub-flujos en un solo diagrama con los tres carriles.

```mermaid
flowchart TD
    %% ===================== ALUMNO =====================
    subgraph AL["🧑 ALUMNO"]
        I((Inicio)) --> Q1{¿Tiene cuenta?}
        Q1 -->|Si| LOGIN[Iniciar sesion con Google]
        Q1 -->|No| REG[Registrarse / Onboarding]
        QDES{¿Que desea hacer?}
        PREG[Escribir pregunta]
        MODOSEL[Elegir modo Directo/Socratico]
        RESPQUIZ[Responder quiz]
        FB[Dar feedback 👍/👎]
        Q5{¿Otra pregunta?}
        FIN((Fin))
    end

    %% ===================== DOCENTE =====================
    subgraph DOC["🎓 DOCENTE"]
        SUB[Subir documento PDF/PPTX]
        CQ[Crear quiz por semanas]
        ANA[Consultar analitica]
    end

    %% ===================== SISTEMA =====================
    subgraph SIS["⚙️ SISTEMA (IA + RAG)"]
        VAL[Validar dominio @tecsup]
        HOME[Mostrar pantalla principal]
        ROL{¿Que rol?}

        %% Ingesta
        CHUNK[Extraer texto + chunking]
        AND{AND}
        EMB1[Generar embeddings]
        SAVEC[(Guardar chunks Firestore)]
        SAVEG[(Guardar PDF en Cloud Storage)]
        DOCOK((Documento listo))

        %% Chat RAG
        Q2{¿Historial y\npregunta ambigua?}
        REW[Reescribir consulta]
        EMB2[Embedding de consulta]
        BUS[Buscar fragmentos top-k coseno]
        Q3{¿Encontro material?}
        REUSE[Reusar fragmentos\ndel turno anterior]
        ENS[Ensamblar prompt\ncontexto + modo + historial]
        MODO{¿Modo pedagogico?}
        DIR[Respuesta directa con citas]
        SOC{¿Rendicion o ya\nrazono lo esencial?}
        GUIA[Pista / pregunta guia\nsin citas]
        SINT[Sintesis final con citas]
        SHOW[Mostrar respuesta\nstreaming SSE]
        SAVEM[(Guardar mensaje + citas)]

        %% Quiz
        QGEN[Generar preguntas con IA]
        CALIF[Calificar y guardar intento]

        %% Analitica
        METRIC[Agregar metricas]
        PANEL[Mostrar panel]
        FINDOC((Fin))
    end

    %% ---------- Autenticacion ----------
    LOGIN --> VAL
    REG --> VAL
    VAL --> HOME --> ROL
    ROL -->|Docente| RDOC{¿Que accion?}
    ROL -->|Alumno| QDES

    %% ---------- Docente: acciones ----------
    RDOC -->|Subir material| SUB
    RDOC -->|Crear quiz| CQ
    RDOC -->|Ver analitica| ANA

    %% ---------- Ingesta ----------
    SUB --> CHUNK --> AND
    AND --> EMB1 --> SAVEC --> DOCOK
    AND --> SAVEG

    %% ---------- Quiz (docente genera) ----------
    CQ --> QGEN

    %% ---------- Analitica ----------
    ANA --> METRIC --> PANEL --> FINDOC

    %% ---------- Alumno elige actividad ----------
    QDES -->|Conversar| PREG
    QDES -->|Practicar| RESPQUIZ

    %% ---------- Chat RAG ----------
    PREG --> MODOSEL --> Q2
    Q2 -->|Si| REW --> EMB2
    Q2 -->|No| EMB2
    EMB2 --> BUS --> Q3
    Q3 -->|No| REUSE --> ENS
    Q3 -->|Si| ENS
    ENS --> MODO
    MODO -->|Directo| DIR --> SHOW
    MODO -->|Socratico| SOC
    SOC -->|No| GUIA --> SHOW
    SOC -->|Si| SINT --> SHOW
    SHOW --> FB --> SAVEM --> Q5
    Q5 -->|Si| PREG
    Q5 -->|No| FIN

    %% ---------- Quiz (alumno responde) ----------
    RESPQUIZ --> CALIF --> Q5

    %% ===================== ESTILOS =====================
    classDef store fill:#dbeafe,stroke:#3b82f6,color:#0f172a;
    classDef gate fill:#fef9c3,stroke:#ca8a04,color:#0f172a;
    classDef ev fill:#dcfce7,stroke:#16a34a,color:#0f172a;
    class SAVEC,SAVEG,SAVEM store;
    class Q1,QDES,Q2,Q3,Q5,ROL,RDOC,MODO,SOC,AND gate;
    class I,FIN,DOCOK,FINDOC ev;
```

---

## Diferencias clave vs. el BPMN anterior

| Aspecto | BPMN antiguo | Sistema real (este documento) |
|---|---|---|
| Autenticación | Salidas Si/No invertidas | Google OAuth + dominio restringido |
| Actor Docente | Ausente | Sube docs, crea quizzes, ve analítica |
| Modelo de tutoría | "Ejercicios" (generar/corregir/resolver) | Chat RAG con citas del material |
| Modos pedagógicos | No existían | Directo y Socrático |
| Pipeline RAG | Ausente | Ingesta → embeddings → búsqueda → Gemini |
| Reescritura de consulta | — | Contextualiza seguimientos cortos |
| Feedback | — | 👍/👎 por respuesta |
| "Guardar en Memoria de IA" | Paso final difuso | Mensajes en Firestore + memoria de turnos |
