"""Evaluación cuantitativa del RAG — para la tesis.

Mide Precision@k y Recall@k comparando los documentos recuperados contra
un conjunto de preguntas con respuesta conocida (ground truth).

Uso:
    python tests/eval_rag.py --curso-id <ID> [--top-k 3] [--score-minimo 0.3]

Requiere que el backend esté configurado con credenciales GCP y que el curso
indicado tenga los documentos cargados en Firestore/BigQuery.

Métricas:
    Precision@k  = (chunks recuperados cuyo doc era esperado) / k
    Recall@k     = (docs esperados encontrados en top-k) / total_docs_esperados
    Hit Rate     = fracción de preguntas donde al menos 1 doc esperado aparece
"""
import argparse
import json
import sys
import os

# Ajustar path para importar desde el proyecto.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ── Ground truth ──────────────────────────────────────────────────────────────
# Formato: {"pregunta": ..., "docs_esperados": [nombre_parcial_del_doc, ...]}
# Edita estas entradas para tu curso. El nombre es parcial (substring) para
# tolerar variaciones en el nombre de archivo.
PREGUNTAS_EVAL: list[dict] = [
    {
        "pregunta": "¿Qué es el análisis FODA?",
        "docs_esperados": ["FODA", "foda"],
    },
    {
        "pregunta": "¿Cuáles son los elementos internos del FODA?",
        "docs_esperados": ["FODA", "foda"],
    },
    {
        "pregunta": "¿Qué es el perfil del egresado de TECSUP?",
        "docs_esperados": ["Perfil", "perfil", "egresado"],
    },
    {
        "pregunta": "¿Cuáles son las competencias del egresado?",
        "docs_esperados": ["Perfil", "perfil", "egresado", "competencia"],
    },
    {
        "pregunta": "¿Cómo se aplica la consultoría en empresas?",
        "docs_esperados": ["consultor", "Consultor"],
    },
]


def _doc_esperado(nombre_doc: str, docs_esperados: list[str]) -> bool:
    nombre = nombre_doc.lower()
    return any(exp.lower() in nombre for exp in docs_esperados)


def evaluar(curso_id: str, top_k: int, score_minimo: float) -> dict:
    from app.core.firestore_client import get_db
    from app.core.rag import recuperar_chunks
    from app.core.firebase import init_firebase

    init_firebase()
    db = next(get_db())

    precision_list: list[float] = []
    recall_list: list[float] = []
    hits: int = 0

    resultados: list[dict] = []

    for item in PREGUNTAS_EVAL:
        pregunta = item["pregunta"]
        docs_esp = item["docs_esperados"]

        chunks = recuperar_chunks(
            curso_id, pregunta, db, top_k=top_k, score_minimo=score_minimo
        )

        recuperados = [c["nombre_doc"] for c in chunks]
        correctos = sum(1 for d in recuperados if _doc_esperado(d, docs_esp))
        docs_encontrados = len({
            d for d in recuperados if _doc_esperado(d, docs_esp)
        })

        p = correctos / top_k if top_k > 0 else 0.0
        r = docs_encontrados / len(docs_esp) if docs_esp else 0.0
        hit = docs_encontrados > 0

        precision_list.append(p)
        recall_list.append(r)
        if hit:
            hits += 1

        resultados.append({
            "pregunta": pregunta,
            "docs_esperados": docs_esp,
            "recuperados": recuperados,
            "precision": round(p, 3),
            "recall": round(r, 3),
            "hit": hit,
        })

    n = len(PREGUNTAS_EVAL)
    resumen = {
        "curso_id": curso_id,
        "top_k": top_k,
        "score_minimo": score_minimo,
        "n_preguntas": n,
        "mean_precision": round(sum(precision_list) / n, 3) if n else 0.0,
        "mean_recall": round(sum(recall_list) / n, 3) if n else 0.0,
        "hit_rate": round(hits / n, 3) if n else 0.0,
        "detalle": resultados,
    }
    return resumen


def main():
    parser = argparse.ArgumentParser(description="Evalúa el pipeline RAG de ProfeTEC.")
    parser.add_argument("--curso-id", required=True, help="ID del curso en Firestore")
    parser.add_argument("--top-k", type=int, default=3, help="Número de chunks a recuperar")
    parser.add_argument("--score-minimo", type=float, default=0.3, help="Score mínimo de similitud")
    parser.add_argument("--json", action="store_true", help="Salida en JSON puro (para scripts)")
    args = parser.parse_args()

    print(f"Evaluando RAG — curso={args.curso_id}, top_k={args.top_k}, score_minimo={args.score_minimo}\n")
    resumen = evaluar(args.curso_id, args.top_k, args.score_minimo)

    if args.json:
        print(json.dumps(resumen, ensure_ascii=False, indent=2))
        return

    print(f"{'Pregunta':<55} {'P@k':>6} {'R@k':>6} {'Hit':>5}")
    print("-" * 78)
    for d in resumen["detalle"]:
        hit_str = "✓" if d["hit"] else "✗"
        print(f"{d['pregunta'][:54]:<55} {d['precision']:>6.3f} {d['recall']:>6.3f} {hit_str:>5}")
    print("-" * 78)
    print(
        f"{'MEDIA':<55} {resumen['mean_precision']:>6.3f} {resumen['mean_recall']:>6.3f} "
        f"Hit Rate: {resumen['hit_rate']:.1%}"
    )
    print()
    print("Interpretación:")
    print(f"  Precision@{args.top_k}: de cada {args.top_k} chunks recuperados, "
          f"{resumen['mean_precision']*100:.1f}% venían del documento correcto.")
    print(f"  Recall@{args.top_k}:    el {resumen['mean_recall']*100:.1f}% de los documentos "
          f"esperados aparecieron en el top-{args.top_k}.")
    print(f"  Hit Rate:    el {resumen['hit_rate']:.1%} de las preguntas tuvo al menos 1 acierto.")


if __name__ == "__main__":
    main()
