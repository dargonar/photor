"""SQLite database for photor map history."""

import json
import os
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

DB_DIR = Path(__file__).resolve().parent.parent
DB_PATH = DB_DIR / "photor.db"

_local = threading.local()


def _get_conn() -> sqlite3.Connection:
    """Get thread-local connection."""
    if not hasattr(_local, "conn") or _local.conn is None:
        _local.conn = sqlite3.connect(str(DB_PATH))
        _local.conn.row_factory = sqlite3.Row
        _local.conn.execute("PRAGMA journal_mode=WAL")
        _local.conn.execute("PRAGMA foreign_keys=ON")
    return _local.conn


def init_db():
    """Create tables if they don't exist."""
    conn = _get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS queries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            title TEXT NOT NULL DEFAULT '',
            request_json TEXT NOT NULL DEFAULT '{}',
            result_path TEXT NOT NULL DEFAULT '',
            stats_json TEXT NOT NULL DEFAULT '{}',
            session TEXT DEFAULT '',
            project TEXT DEFAULT ''
        )
    """)
    conn.commit()


def save_query(request: dict, result_path: str, stats: dict) -> int:
    """Save a query execution to the database. Returns the row id."""
    conn = _get_conn()

    # Auto-generate title from queries
    queries = request.get("queries", [])
    title_parts = []
    for q in queries[:4]:
        emoji = q.get("emoji", "")
        titulo = q.get("titulo", "")
        if titulo:
            title_parts.append(f"{emoji} {titulo}" if emoji else titulo)
    title = " · ".join(title_parts) if title_parts else f"Mapa {datetime.now():%H:%M}"

    created_at = datetime.now(timezone.utc).isoformat()
    session = request.get("session", "")
    project = request.get("project", "")

    cur = conn.execute(
        """INSERT INTO queries (created_at, title, request_json, result_path, stats_json, session, project)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (created_at, title, json.dumps(request), result_path, json.dumps(stats), session, project),
    )
    conn.commit()
    return cur.lastrowid


def list_queries(limit: int = 50) -> list[dict]:
    """List recent queries, newest first."""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT id, created_at, title, result_path, stats_json, session, project "
        "FROM queries ORDER BY created_at DESC LIMIT ?", (limit,)
    ).fetchall()
    results = []
    for r in rows:
        stats = json.loads(r["stats_json"]) if r["stats_json"] else {}
        results.append({
            "id": r["id"],
            "created_at": r["created_at"],
            "title": r["title"],
            "result_path": r["result_path"],
            "stats": stats,
            "session": r["session"] or None,
            "project": r["project"] or None,
        })
    return results


def get_query(query_id: int) -> Optional[dict]:
    """Get a single query by id."""
    conn = _get_conn()
    r = conn.execute(
        "SELECT id, created_at, title, request_json, result_path, stats_json, session, project "
        "FROM queries WHERE id = ?", (query_id,)
    ).fetchone()
    if r is None:
        return None
    return {
        "id": r["id"],
        "created_at": r["created_at"],
        "title": r["title"],
        "request": json.loads(r["request_json"]) if r["request_json"] else {},
        "result_path": r["result_path"],
        "stats": json.loads(r["stats_json"]) if r["stats_json"] else {},
        "session": r["session"] or None,
        "project": r["project"] or None,
    }


def delete_query(query_id: int) -> bool:
    """Delete a query by id. Returns True if deleted."""
    conn = _get_conn()
    cur = conn.execute("DELETE FROM queries WHERE id = ?", (query_id,))
    conn.commit()
    return cur.rowcount > 0