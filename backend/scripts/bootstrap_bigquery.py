"""CLI idempotente para crear/migrar el esquema BigQuery del RAG.

Crea (si faltan) el dataset, la tabla de chunks y el indice vectorial usando la
configuracion de `app.config.settings` (BIGQUERY_DATASET, BIGQUERY_CHUNKS_TABLE,
BIGQUERY_LOCATION, GCP_PROJECT_ID / FIREBASE_PROJECT_ID).

Uso (desde el directorio backend/):

    python -m scripts.bootstrap_bigquery
        Crea dataset + tabla + indice si no existen. No toca un indice ya creado.

    python -m scripts.bootstrap_bigquery --recreate-index
        Dropea y recrea el indice vectorial. Necesario una sola vez para migrar
        un indice antiguo creado sin `STORING (curso_id, semana)`.
"""
import argparse
import logging

from app.core.bigquery_rag import ensure_schema


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--recreate-index",
        action="store_true",
        help="Dropea y recrea el indice vectorial (para añadir STORING).",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    ensure_schema(recreate_index=args.recreate_index)
    print("Esquema BigQuery del RAG listo.")


if __name__ == "__main__":
    main()
