"""HTTP server for photor map Web UI.

No SigLIP loading: map generation is delegated to CLI subprocesses.
SQLite for query history persistence.

Usage:
    python3 -m photor serve --port 9000
"""

import json
import logging
import os
import re
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs

from . import db
from .chroma import get_client, get_collection, list_sessions, get_stats

logger = logging.getLogger("photor.serve")

HERE = Path(__file__).resolve().parent
STATIC_DIR = HERE / "server_static"
MAPS_DIR = HERE.parent / "maps"
CLI_CMD = [sys.executable, "-m", "photor.cli", "map"]

# ── Helpers ────────────────────────────────────────────────────────

def json_response(handler, data, status=200):
    """Send JSON response."""
    body = json.dumps(data, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def error_response(handler, message, status=400):
    json_response(handler, {"error": message}, status)


def read_body(handler) -> str:
    """Read request body."""
    length = int(handler.headers.get("Content-Length", 0))
    if length == 0:
        return ""
    return handler.rfile.read(length).decode("utf-8")


def time_ago(iso_str: str) -> str:
    """Convert ISO timestamp to relative time string."""
    try:
        dt = datetime.fromisoformat(iso_str)
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        diff = now - dt.replace(tzinfo=None)
        seconds = diff.total_seconds()
        if seconds < 60:
            return "ahora"
        minutes = int(seconds / 60)
        if minutes < 60:
            return f"hace {minutes} min"
        hours = int(minutes / 60)
        if hours < 24:
            return f"hace {hours}h"
        days = int(hours / 24)
        return f"hace {days}d"
    except Exception:
        return iso_str


def generate_map_title(request: dict) -> str:
    """Auto-generate a title from the request."""
    queries = request.get("queries", [])
    parts = []
    for q in queries[:4]:
        emoji = q.get("emoji", "")
        titulo = q.get("titulo", "")
        if titulo:
            parts.append(f"{emoji} {titulo}" if emoji else titulo)
    if not parts:
        return f"Mapa {datetime.now():%H:%M}"
    return " · ".join(parts)


# ── Routes ─────────────────────────────────────────────────────────

def route(handler):
    """Route a request to the appropriate handler."""
    path = handler.path.split("?")[0]
    method = handler.command

    # API routes first
    if path == "/api/sessions" and method == "GET":
        return api_sessions(handler)
    if path == "/api/projects" and method == "GET":
        return api_projects(handler)
    if path == "/api/queries" and method == "GET":
        return api_queries_list(handler)
    m = re.match(r"^/api/queries/delete/(\d+)$", path)
    if m and method == "POST":
        return api_queries_delete(handler, int(m.group(1)))
    if path == "/api/tree" and method == "GET":
        return api_tree(handler)
    if path == "/api/map" and method == "POST":
        return api_map_run(handler)
    if path == "/api/map-file" and method == "GET":
        return api_map_file(handler)

    # Static files: serve from STATIC_DIR
    # Map / → index.html, /static/X → X (strip /static/ prefix)
    if path in ("/", ""):
        rel = "index.html"
    elif path.startswith("/static/"):
        rel = path[len("/static/"):]
    elif path.startswith("/"):
        rel = path.lstrip("/")
    else:
        rel = path

    # Security: prevent directory traversal
    if ".." in rel or rel.startswith("/"):
        error_response(handler, "Invalid path", 403)
        return

    filepath = STATIC_DIR / rel
    if not filepath.exists() or not filepath.is_file():
        error_response(handler, "File not found", 404)
        return

    content_types = {
        ".html": "text/html; charset=utf-8",
        ".css": "text/css; charset=utf-8",
        ".js": "application/javascript; charset=utf-8",
        ".json": "application/json",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".svg": "image/svg+xml",
        ".ico": "image/x-icon",
    }
    ctype = content_types.get(filepath.suffix.lower(), "application/octet-stream")

    handler.send_response(200)
    handler.send_header("Content-Type", ctype)
    handler.send_header("Cache-Control", "no-cache")
    handler.end_headers()
    with open(filepath, "rb") as f:
        handler.wfile.write(f.read())


def serve_static(handler, rel_path: str):
    """Serve a file from STATIC_DIR."""
    if rel_path == "/index.html":
        rel_path = "index.html"
    if ".." in rel_path or rel_path.startswith("/"):
        error_response(handler, "Invalid path", 403)
        return

    filepath = STATIC_DIR / rel_path
    if not filepath.exists() or not filepath.is_file():
        error_response(handler, "File not found", 404)
        return

    # Determine content type
    ext = filepath.suffix.lower()
    content_types = {
        ".html": "text/html; charset=utf-8",
        ".css": "text/css; charset=utf-8",
        ".js": "application/javascript; charset=utf-8",
        ".json": "application/json",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".svg": "image/svg+xml",
        ".ico": "image/x-icon",
    }
    ctype = content_types.get(ext, "application/octet-stream")

    handler.send_response(200)
    handler.send_header("Content-Type", ctype)
    handler.send_header("Cache-Control", "no-cache")
    handler.end_headers()
    with open(filepath, "rb") as f:
        handler.wfile.write(f.read())


def api_sessions(handler):
    """GET /api/sessions — list available sessions."""
    cfg = _load_config()
    db_path = cfg.get("chroma", {}).get("path", "/media/dargonar/bkp_1t_new/photo_index")
    collection_name = cfg.get("chroma", {}).get("collection", "photos")
    sessions = list_sessions(db_path, collection_name)
    data = [{"name": s, "count": c} for s, c in sessions.items()]
    json_response(handler, {"sessions": data})


def api_projects(handler):
    """GET /api/projects — list available projects."""
    cfg = _load_config()
    db_path = cfg.get("chroma", {}).get("path", "/media/dargonar/bkp_1t_new/photo_index")
    collection_name = cfg.get("chroma", {}).get("collection", "photos")
    stats = get_stats(db_path, collection_name)
    projects = stats.get("projects", {})
    data = [{"name": p, "count": c} for p, c in projects.items()]
    json_response(handler, {"projects": data})


def api_tree(handler):
    """GET /api/tree — project → session → set hierarchy with counts."""
    cfg = _load_config()
    db_path = cfg.get("chroma", {}).get("path", "/media/dargonar/bkp_1t_new/photo_index")
    collection_name = cfg.get("chroma", {}).get("collection", "photos")

    client = get_client(db_path)
    try:
        collection = get_collection(client, collection_name, create=False)
    except ValueError:
        json_response(handler, {"projects": []})
        return

    all_data = collection.get(include=["metadatas"])
    tree = {}  # project → {session → {set → count}}
    for m in all_data["metadatas"]:
        if not m:
            continue
        p = m.get("project") or m.get("session", "unknown")
        s = m.get("session", "unknown")
        t = m.get("set", "default")
        if p not in tree:
            tree[p] = {}
        if s not in tree[p]:
            tree[p][s] = {}
        tree[p][s][t] = tree[p][s].get(t, 0) + 1

    result = []
    for p in sorted(tree):
        sessions = []
        for s in sorted(tree[p]):
            sets = [{"name": t, "count": c} for t, c in sorted(tree[p][s].items())]
            total = sum(c for _, c in tree[p][s].items())
            sessions.append({"name": s, "total": total, "sets": sets})
        result.append({"name": p, "sessions": sessions})
    json_response(handler, {"projects": result})


def api_queries_list(handler):
    """GET /api/queries — list all saved queries."""
    queries = db.list_queries()
    # Add relative time
    for q in queries:
        q["time_ago"] = time_ago(q["created_at"])
    json_response(handler, {"queries": queries})


def api_queries_delete(handler, query_id: int):
    """POST /api/queries/delete/<id> — delete a query."""
    ok = db.delete_query(query_id)
    if ok:
        json_response(handler, {"status": "deleted", "id": query_id})
    else:
        error_response(handler, f"Query {query_id} not found", 404)


def _load_config():
    """Load photor.yaml config."""
    from .utils import load_config
    return load_config()


def _find_photor_cli() -> list[str]:
    """Find the photor CLI command."""
    # Use the same python, invoke as module
    return [sys.executable, "-m", "photor", "map"]


def api_map_file(handler):
    """GET /api/map-file — serve a generated HTML map file."""
    from urllib.parse import urlparse, parse_qs
    qs = parse_qs(urlparse(handler.path).query)
    paths = qs.get("path", [])
    if not paths:
        error_response(handler, "Missing path parameter", 400)
        return
    filepath = paths[0]
    if not os.path.exists(filepath):
        error_response(handler, f"File not found: {filepath}", 404)
        return
    is_download = "download" in qs

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    if is_download:
        handler.send_response(200)
        handler.send_header("Content-Type", "text/html; charset=utf-8")
        handler.send_header("Content-Disposition", f'attachment; filename="{os.path.basename(filepath)}"')
        handler.end_headers()
        handler.wfile.write(content.encode("utf-8"))
    else:
        json_response(handler, {"html": content})


def api_map_run(handler):
    """POST /api/map — run a concept map query via CLI subprocess."""
    body = read_body(handler)
    if not body:
        error_response(handler, "Empty request body", 400)
        return

    try:
        request = json.loads(body)
    except json.JSONDecodeError as e:
        error_response(handler, f"Invalid JSON: {e}", 400)
        return

    queries = request.get("queries", [])
    if not queries:
        error_response(handler, "No queries provided", 400)
        return

    # Validate queries
    for q in queries:
        if not q.get("query", "").strip():
            error_response(handler, "Each query must have a 'query' field", 400)
            return

    # Write queries to temp file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(queries, f, ensure_ascii=False)
        queries_path = f.name

    # Determine output path
    os.makedirs(str(MAPS_DIR), exist_ok=True)
    output_path = _next_filename(str(MAPS_DIR))
    output_path_str = str(output_path)

    # Build filter args
    filters = {
        "session": request.get("session", ""),
        "project": request.get("project", ""),
        "set": request.get("set", ""),
        "color": request.get("color", ""),
        "orientacion": request.get("orientacion", ""),
        "personajes": request.get("personajes", ""),
    }
    filter_args = []
    for k, v in filters.items():
        if v:
            filter_args.extend([f"--{k.replace('_', '-')}", v])

    n_results = request.get("n_results", 15)
    nodal_top = request.get("nodal_top", 10)
    dark = request.get("dark", True)

    # Build CLI command
    cmd = _find_photor_cli() + [
        queries_path,
        "-n", str(n_results),
        "--nodal-top", str(nodal_top),
        "--dark" if dark else "--light",
        "-o", output_path_str,
    ] + filter_args

    logger.info(f"Ejecutando: {' '.join(cmd)}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,  # 10 min timeout
            cwd=str(Path(__file__).resolve().parent.parent),
        )

        # Clean up temp queries file
        try:
            os.unlink(queries_path)
        except Exception:
            pass

        if result.returncode != 0:
            error_msg = result.stderr or result.stdout or "Unknown error"
            logger.error(f"CLI error: {error_msg}")
            json_response(handler, {
                "error": f"Error generando mapa: {error_msg}",
                "stderr": result.stderr,
                "stdout": result.stdout,
            }, 500)
            return

        # Check if output file exists
        if not os.path.exists(output_path_str):
            json_response(handler, {
                "error": "No se generó el archivo HTML de salida",
                "stdout": result.stdout,
                "stderr": result.stderr,
            }, 500)
            return

        # Don't read the HTML — just return the path
        # Compute basic stats from the CLI output
        stats = {
            "total_entries": len(queries) * n_results,
            "unique_photos": 0,
            "concepts": len(queries),
        }
        # Try to extract unique photo count from CLI output
        for line in (result.stdout or "").split("\n"):
            if "fotos únicas" in line:
                import re
                m = re.search(r'(\d+)\s+fotos', line)
                if m:
                    stats["unique_photos"] = int(m.group(1))
                break

        # Save to SQLite
        query_id = db.save_query(request, output_path_str, stats)

        # Response
        json_response(handler, {
            "id": query_id,
            "path": output_path_str,
            "stats": stats,
            "title": generate_map_title(request),
            "created_at": datetime.now(timezone.utc).isoformat(),
        })

    except subprocess.TimeoutExpired:
        try:
            os.unlink(queries_path)
        except Exception:
            pass
        error_response(handler, "Timeout: la generación del mapa tomó más de 10 minutos", 504)

    except Exception as e:
        try:
            os.unlink(queries_path)
        except Exception:
            pass
        logger.exception("Error in api_map_run")
        error_response(handler, str(e), 500)


def _next_filename(directory: str, prefix: str = "mapeo", ext: str = ".html") -> Path:
    """Generate auto-incremental filename."""
    import re
    os.makedirs(directory, exist_ok=True)
    max_num = 0
    pattern = re.compile(rf"^{re.escape(prefix)}_(\d+){re.escape(ext)}$")
    for f in os.listdir(directory):
        m = pattern.match(f)
        if m:
            n = int(m.group(1))
            if n > max_num:
                max_num = n
    return Path(directory) / f"{prefix}_{max_num + 1:03d}{ext}"


# ── Server ─────────────────────────────────────────────────────────

class PhotorHandler(SimpleHTTPRequestHandler):
    """HTTP request handler that routes API calls."""

    def do_GET(self):
        route(self)

    def do_POST(self):
        route(self)

    def log_message(self, format, *args):
        logger.info(format % args)

    # Suppress default directory listing
    def list_directory(self, path):
        error_response(self, "Not found", 404)


def serve(host: str = "0.0.0.0", port: int = 9000):
    """Start the photor map web server."""
    # Initialize database
    db.init_db()

    # Ensure static and maps dirs exist
    STATIC_DIR.mkdir(parents=True, exist_ok=True)
    MAPS_DIR.mkdir(parents=True, exist_ok=True)

    server = HTTPServer((host, port), PhotorHandler)
    print(f"📷 photor map — Web UI")
    print(f"   http://localhost:{port}")
    print(f"   Presiona Ctrl+C para detener")
    print()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Servidor detenido")
        server.server_close()