"""Generación de preguntas tipo quiz a partir del material del curso (RF-20..RF-21).

Estrategia:
1. Recuperar chunks relevantes con RAG (si hay tema) o un muestreo del curso.
2. Construir un prompt que pida a Gemini un JSON con preguntas de opción múltiple.
3. Parsear, validar y normalizar el resultado.
"""
import json
import logging
import re

from app.config import settings
from app.core.gemini import generar_json, generar_texto
from app.core.rag import recuperar_chunks

logger = logging.getLogger(__name__)


def _sample_chunks_curso(
    curso_id: str,
    db,
    limite: int,
    semana_desde: int | None = None,
    semana_hasta: int | None = None,
) -> list[dict]:
    """Toma una muestra de chunks del curso sin filtrar por similitud."""
    query = (
        db.collection("chunks")
        .where("curso_id", "==", curso_id)
        .limit(settings.rag_max_chunks_scan)
    )
    out: list[dict] = []
    for doc in query.stream():
        data = doc.to_dict() or {}
        semana = data.get("semana")
        if semana_desde is not None or semana_hasta is not None:
            if semana is None:
                continue
            try:
                semana_int = int(semana)
            except (TypeError, ValueError):
                continue
            if semana_desde is not None and semana_int < semana_desde:
                continue
            if semana_hasta is not None and semana_int > semana_hasta:
                continue
        else:
            semana_int = int(semana) if semana is not None else None
        out.append({
            "documento_id": data.get("documento_id", ""),
            "nombre_doc": data.get("nombre_doc", ""),
            "pagina": data.get("pagina", 1),
            "semana": semana_int,
            "texto": data.get("texto", ""),
        })
        if len(out) >= limite:
            break
    return out


def _construir_prompt(chunks: list[dict], tema: str | None, num: int) -> str:
    contexto_partes = []
    for i, c in enumerate(chunks, 1):
        contexto_partes.append(
            f"[Fragmento {i} — {c.get('nombre_doc')}, pág. {c.get('pagina')}]\n"
            f"{c.get('texto', '')}"
        )
    contexto = "\n\n---\n\n".join(contexto_partes) if contexto_partes else "(sin material disponible)"

    tema_txt = f"Tema solicitado: {tema}\n" if tema else "Tema: cobertura general del material entregado.\n"

    return (
        "Eres ProfeTEC.IA. Genera un cuestionario de opción múltiple "
        "exclusivamente a partir del material del curso entregado a continuación. "
        "No inventes contenido fuera de los fragmentos.\n\n"
        f"{tema_txt}"
        f"Cantidad de preguntas: {num}\n"
        "Reglas de formato (críticas para que el JSON quepa):\n"
        "- Cada pregunta tiene exactamente 4 opciones.\n"
        "- Cada opción es una frase corta, máximo 18 palabras.\n"
        "- 'texto' de la pregunta: máximo 30 palabras.\n"
        "- 'explicacion': una sola oración breve.\n"
        "- 'indice_correcto' es el índice (0..3) de la opción correcta.\n"
        "- Si la pregunta proviene de un fragmento, anota documento y página.\n\n"
        "Material del curso:\n\n"
        f"{contexto}\n\n"
        "Devuelve ÚNICAMENTE un JSON válido (sin ```), sin texto adicional, con esta forma:\n"
        "{\n"
        '  "preguntas": [\n'
        "    {\n"
        '      "texto": "...",\n'
        '      "opciones": ["A", "B", "C", "D"],\n'
        '      "indice_correcto": 0,\n'
        '      "explicacion": "...",\n'
        '      "nombre_doc": "...",\n'
        '      "pagina": 1\n'
        "    }\n"
        "  ]\n"
        "}\n"
    )


def _intentar_reparar_truncado(raw: str) -> str | None:
    """Si el JSON viene truncado (preguntas[] sin cerrar), intenta recortar a la
    última pregunta completa y cerrar los corchetes. Retorna el JSON reparado
    o None si no se puede salvar."""
    # Localizar el último '},' o '}' dentro de preguntas[] y cortar ahí.
    inicio = raw.find('"preguntas"')
    if inicio < 0:
        return None
    bracket = raw.find('[', inicio)
    if bracket < 0:
        return None
    # Encontrar el último '}' de un objeto pregunta que tenga al menos texto y opciones.
    # Heurística: cortar después del último '}' antes del final.
    ultimo_cierre = raw.rfind('}')
    if ultimo_cierre <= bracket:
        return None
    reparado = raw[: ultimo_cierre + 1] + "]}"
    try:
        json.loads(reparado)
        return reparado
    except (json.JSONDecodeError, ValueError):
        return None


def _parse_json_safe(raw: str) -> dict:
    """Extrae el JSON de la respuesta del modelo, tolerando bloques de código y
    truncamiento parcial."""
    raw = (raw or "").strip()
    if not raw:
        raise ValueError("El modelo devolvió una respuesta vacía.")
    # Quitar fences cerrados: ```json ... ```
    fence = re.match(r"^```(?:json)?\s*([\s\S]*?)\s*```\s*$", raw)
    if fence:
        raw = fence.group(1).strip()
    else:
        # Fence abierto sin cerrar (común cuando el modelo se trunca)
        open_fence = re.match(r"^```(?:json)?\s*", raw)
        if open_fence:
            raw = raw[open_fence.end():].strip()
    # Si hay texto antes del JSON, recortar desde la primera llave.
    if not raw.startswith("{"):
        idx = raw.find("{")
        if idx >= 0:
            raw = raw[idx:].strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    # Segundo intento: bloque entre la primera y la última llave (descarta basura final)
    m = re.search(r"\{[\s\S]*\}", raw)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            pass
    # Último intento: reparar JSON truncado cerrando preguntas[] y objeto raíz
    reparado = _intentar_reparar_truncado(raw)
    if reparado:
        return json.loads(reparado)
    # Si nada funciona, propagar el error original
    return json.loads(raw)


def _validar_pregunta(p: dict) -> dict:
    """Normaliza y valida una pregunta del modelo. Lanza ValueError si es inválida."""
    texto = (p.get("texto") or "").strip()
    opciones_raw = p.get("opciones") or []
    if not texto or not isinstance(opciones_raw, list) or len(opciones_raw) < 2:
        raise ValueError("pregunta sin texto u opciones válidas")
    opciones = [str(o).strip() for o in opciones_raw if str(o).strip()]
    if len(opciones) < 2:
        raise ValueError("pregunta con menos de 2 opciones")
    indice = int(p.get("indice_correcto", 0))
    if indice < 0 or indice >= len(opciones):
        indice = 0
    pagina = p.get("pagina")
    try:
        pagina_int = int(pagina) if pagina is not None else None
    except (TypeError, ValueError):
        pagina_int = None
    return {
        "texto": texto[:600],
        "opciones": opciones[:5],
        "indice_correcto": indice,
        "explicacion": (p.get("explicacion") or "").strip()[:500] or None,
        "nombre_doc": (p.get("nombre_doc") or "").strip()[:200] or None,
        "pagina": pagina_int,
    }


def generar_preguntas(
    curso_id: str,
    tema: str | None,
    num_preguntas: int,
    db,
    semana_desde: int | None = None,
    semana_hasta: int | None = None,
) -> list[dict]:
    """Devuelve una lista de preguntas validadas."""
    if tema and semana_desde is None and semana_hasta is None:
        chunks = recuperar_chunks(curso_id, tema, db, top_k=min(num_preguntas + 2, 8))
    else:
        chunks = _sample_chunks_curso(
            curso_id,
            db,
            limite=num_preguntas * 3,
            semana_desde=semana_desde,
            semana_hasta=semana_hasta,
        )

    if not chunks:
        raise ValueError(
            "El curso no tiene material indexado. Sube documentos antes de generar un quiz."
        )

    prompt = _construir_prompt(chunks, tema, num_preguntas)
    # Tope de tokens generoso: Gemini 2.5 Flash soporta hasta 8192 tokens de salida y
    # cada pregunta con 4 opciones largas en español puede pesar ~600 tokens.
    max_tokens = min(8192, max(4096, num_preguntas * 700))

    raw = ""
    last_error: Exception | None = None
    for intento in range(2):
        # Primer intento en modo JSON nativo; segundo intento en modo texto si vino vacío.
        if intento == 0:
            raw = generar_json(prompt, temperatura=0.4, max_tokens=max_tokens)
        else:
            raw = generar_texto(prompt, temperatura=0.6, max_tokens=max_tokens)
        try:
            data = _parse_json_safe(raw)
            break
        except (json.JSONDecodeError, ValueError) as exc:
            last_error = exc
            logger.warning(
                "Salida no parseable del modelo (intento %d). Primeros 300 chars: %r",
                intento + 1,
                raw[:300],
            )
            data = None
    if data is None:
        raise ValueError(
            f"El modelo no devolvió un JSON válido tras dos intentos: {last_error}"
        )

    preguntas_raw = data.get("preguntas") if isinstance(data, dict) else None
    if not isinstance(preguntas_raw, list) or not preguntas_raw:
        raise ValueError("El modelo no devolvió preguntas válidas.")

    validadas: list[dict] = []
    for p in preguntas_raw:
        try:
            validadas.append(_validar_pregunta(p))
        except ValueError:
            continue

    if not validadas:
        raise ValueError("Todas las preguntas devueltas eran inválidas.")

    return validadas[:num_preguntas]
