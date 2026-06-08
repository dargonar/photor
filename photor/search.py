"""Search photos in ChromaDB by semantic concept."""

import logging
from typing import Optional

from . import chroma
from .siglip import SigLipModel
from .utils import media_path

logger = logging.getLogger("photor")


def search_photos(
    query: str,
    session: Optional[str] = None,
    n_results: int = 10,
    db_path: str = "/media/dargonar/bkp_1t_new/photo_index",
    collection_name: str = "photos",
    model_name: str = "google/siglip-so400m-patch14-384",
    device: str = "auto",
) -> list[dict]:
    """Search photos by semantic concept.

    Returns list of dicts with filename, path, session, score.
    """
    # Open ChromaDB
    client = chroma.get_client(db_path)
    try:
        collection = chroma.get_collection(client, collection_name, create=False)
    except ValueError:
        logger.warning(f"❌ Colección '{collection_name}' no existe en {db_path}")
        return []

    # Load model
    model = SigLipModel(model_name, device=device)
    model.load()

    # Encode query
    query_embedding = model.encode_text(query)

    # Build filter
    where_filter = None
    if session:
        where_filter = {"session": session}

    # Search
    results = chroma.search_similar(
        collection, query_embedding,
        n_results=n_results,
        where_filter=where_filter,
    )

    if not results["ids"] or not results["ids"][0]:
        return []

    # Format results
    formatted = []
    for doc_id, distance, metadata in zip(
        results["ids"][0],
        results["distances"][0],
        results["metadatas"][0],
    ):
        score = chroma.cosine_similarity(distance)
        formatted.append({
            "id": doc_id,
            "filename": metadata.get("filename", doc_id) if metadata else doc_id,
            "path": metadata.get("path", "?") if metadata else "?",
            "session": metadata.get("session", "?") if metadata else "?",
            "score": score,
            "media": media_path(metadata.get("path", "")) if metadata else "",
        })

    return formatted


def print_search_results(results: list[dict]):
    """Print search results to console."""
    if not results:
        logger.info("   😕 Sin resultados")
        return

    logger.info("═══════════════════════════════════════")
    logger.info(f"  Top {len(results)} resultados:\n")

    for i, r in enumerate(results):
        logger.info(f"  #{i+1}  {r['filename']}")
        logger.info(f"       Similaridad: {r['score']:.1%}  |  Sesión: {r['session']}")
        logger.info(f"       Path: {r['path']}")
        logger.info("")

    # MEDIA paths for Hermes
    logger.info("═══════════════════════════════════════")
    logger.info("  MEDIA paths:")
    for r in results:
        if r["media"]:
            logger.info(f"  {r['media']}")
    logger.info("═══════════════════════════════════════")


def list_sessions(db_path: str, collection_name: str = "photos"):
    """List all indexed sessions."""
    sessions = chroma.list_sessions(db_path, collection_name)
    if not sessions:
        logger.info("📂 No hay sesiones indexadas")
        return

    logger.info(f"📂 Sesiones disponibles ({len(sessions)}):")
    for s, count in sessions.items():
        logger.info(f"   · {s} ({count} fotos)")


def show_stats(db_path: str, collection_name: str = "photos"):
    """Show ChromaDB statistics."""
    stats = chroma.get_stats(db_path, collection_name)
    logger.info(f"📊 Estadísticas de '{collection_name}':")
    logger.info(f"   Total de fotos indexadas: {stats['total']}")
    if stats["projects"]:
        logger.info(f"   Proyectos:")
        for p, c in stats["projects"].items():
            logger.info(f"     · {p}: {c} fotos")
    if stats["sessions"]:
        logger.info(f"   Sesiones:")
        for s, c in stats["sessions"].items():
            logger.info(f"     · {s}: {c} fotos")