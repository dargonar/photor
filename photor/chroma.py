"""ChromaDB client wrapper for photor."""

import os
from pathlib import Path
from typing import Optional

import chromadb
from chromadb.api.types import Where


def get_client(db_path: str) -> chromadb.PersistentClient:
    """Get or create ChromaDB client."""
    os.makedirs(db_path, exist_ok=True)
    return chromadb.PersistentClient(path=db_path)


def get_collection(client: chromadb.PersistentClient,
                   name: str = "photos",
                   create: bool = True):
    """Get or create a ChromaDB collection."""
    if create:
        return client.get_or_create_collection(name=name)
    return client.get_collection(name=name)


def reset_collection(db_path: str, name: str = "photos"):
    """Delete an entire collection."""
    client = get_client(db_path)
    try:
        client.delete_collection(name=name)
        return True
    except ValueError:
        return False


def list_sessions(db_path: str, collection_name: str = "photos") -> dict[str, int]:
    """List all sessions with photo counts."""
    client = get_client(db_path)
    try:
        collection = get_collection(client, collection_name)
    except ValueError:
        return {}

    all_data = collection.get(include=["metadatas"])
    sessions: dict[str, int] = {}
    for m in all_data["metadatas"]:
        if m and "session" in m:
            s = m["session"]
            sessions[s] = sessions.get(s, 0) + 1
    return dict(sorted(sessions.items()))


def get_stats(db_path: str, collection_name: str = "photos") -> dict:
    """Get database statistics."""
    client = get_client(db_path)
    try:
        collection = get_collection(client, collection_name)
    except ValueError:
        return {"total": 0, "sessions": {}}

    all_data = collection.get(include=["metadatas"])
    total = len(all_data["ids"])
    sessions: dict[str, int] = {}
    projects: dict[str, int] = {}

    for m in all_data["metadatas"]:
        if m:
            s = m.get("session", "unknown")
            sessions[s] = sessions.get(s, 0) + 1
            p = m.get("project", "unknown")
            projects[p] = projects.get(p, 0) + 1

    return {
        "total": total,
        "sessions": dict(sorted(sessions.items())),
        "projects": dict(sorted(projects.items())),
    }


def search_similar(collection, query_embedding: list[float],
                   n_results: int = 10,
                   where_filter: Optional[Where] = None):
    """Search collection by embedding similarity."""
    return collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        where=where_filter,
        include=["metadatas", "distances", "documents"],
    )


def cosine_similarity(l2_sq: float) -> float:
    """Convert ChromaDB's squared L2 to cosine similarity [0, 1]."""
    raw_cos = 1.0 - (l2_sq / 2.0)
    return max(0.0, min(1.0, raw_cos))
