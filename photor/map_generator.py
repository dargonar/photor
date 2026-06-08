"""Generate concept map HTML from ChromaDB semantic queries."""

import json
import logging
import os
import re
from html import escape
from pathlib import Path
from typing import Optional

from . import chroma
from .siglip import SigLipModel

logger = logging.getLogger("photor")


def next_filename(directory: str, prefix: str = "mapeo", ext: str = ".html") -> str:
    """Generate auto-incremental filename: mapeo_001.html, mapeo_002.html..."""
    os.makedirs(directory, exist_ok=True)
    max_num = 0
    pattern = re.compile(rf"^{re.escape(prefix)}_(\d+){re.escape(ext)}$")
    for f in os.listdir(directory):
        m = pattern.match(f)
        if m:
            n = int(m.group(1))
            if n > max_num:
                max_num = n
    return os.path.join(directory, f"{prefix}_{max_num + 1:03d}{ext}")


def build_where(session=None, project=None, set_name=None, variante=None,
                color=None, orientacion=None, personajes=None):
    """Build ChromaDB where filter combining multiple conditions.

    Supports comma-separated values for multi-filtering with $in.
    Ej: session="flor,gero" → {"session": {"$in": ["flor", "gero"]}}
    """
    def _val(v):
        """Parse a value: string → list if comma-separated, else as-is."""
        if not v:
            return None
        if isinstance(v, (list, tuple)):
            return v if len(v) > 1 else v[0]
        v = v.strip()
        if "," in v:
            parts = [p.strip() for p in v.split(",") if p.strip()]
            return parts if len(parts) > 1 else parts[0]
        return v

    def _cond(key, raw):
        val = _val(raw)
        if not val:
            return None
        if isinstance(val, list):
            return {key: {"$in": val}}
        return {key: val}

    conditions = []
    for key, raw in [
        ("session", session), ("project", project), ("set", set_name),
        ("variante", variante), ("color", color), ("orientacion", orientacion),
        ("personajes", personajes),
    ]:
        c = _cond(key, raw)
        if c:
            conditions.append(c)

    if len(conditions) == 0:
        return None
    elif len(conditions) == 1:
        return conditions[0]
    else:
        return {"$and": conditions}


def run_queries(queries: list[dict], n_results: int, model: SigLipModel,
                collection, path_map: Optional[dict] = None, **filters):
    """Execute all queries and return flat list of results."""
    all_photos = []

    for q in queries:
        query_text = q["query"]
        emoji = q.get("emoji", "")
        titulo = q.get("titulo", query_text)

        where_filter = build_where(**filters)

        query_emb = model.encode_text(query_text)
        results = chroma.search_similar(
            collection, query_emb,
            n_results=n_results,
            where_filter=where_filter,
        )

        if not results["ids"] or not results["ids"][0]:
            continue

        for doc_id, distance, meta in zip(
            results["ids"][0],
            results["distances"][0],
            results["metadatas"][0],
        ):
            path = meta.get("path", "?") if meta else "?"
            if path_map:
                for old, new in path_map.items():
                    path = path.replace(old, new)

            score = chroma.cosine_similarity(distance)
            all_photos.append({
                "filename": meta.get("filename", doc_id) if meta else doc_id,
                "path": path,
                "session": meta.get("session", "?") if meta else "?",
                "score": score,
                "emoji": emoji,
                "titulo": titulo,
                "query_text": query_text,
            })

    return all_photos


def build_html(queries: list[dict], all_photos: list[dict],
               title: str = "Mapa conceptual",
               dark: bool = True, max_nodal: int = 10):
    """Generate self-contained HTML with concept clusters and nodal analysis."""

    # Group by concept ordered by query list
    concept_groups = []
    for q in queries:
        key = q["titulo"]
        photos = [p for p in all_photos if p["titulo"] == key]
        if photos:
            # Sort by score descending
            photos.sort(key=lambda x: x["score"], reverse=True)
            concept_groups.append({
                "emoji": q.get("emoji", ""),
                "titulo": key,
                "query_text": q["query"],
                "photos": photos,
            })

    # Nodal analysis
    node_map = {}
    for p in all_photos:
        key = p["path"]
        if key not in node_map:
            node_map[key] = {
                "path": p["path"],
                "filename": p["filename"],
                "session": p["session"],
                "emojis": set(),
                "concepts": set(),
            }
        node_map[key]["emojis"].add(p["emoji"])
        node_map[key]["concepts"].add(p["titulo"])

    nodals = [v for v in node_map.values() if len(v["concepts"]) >= 3]
    bisagras = [v for v in node_map.values() if len(v["concepts"]) == 2]
    nodals.sort(key=lambda x: len(x["concepts"]), reverse=True)
    bisagras.sort(key=lambda x: len(x["concepts"]), reverse=True)

    bg = "#111" if dark else "#f5f5f5"
    fg = "#e0e0e0" if dark else "#222"
    card_bg = "#1a1a1a" if dark else "#fff"
    card_hover = "#252525" if dark else "#f0f0f0"
    sub_fg = "#555" if dark else "#888"

    # Build HTML
    lines = []
    lines.append(f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{escape(title)}</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: {bg}; color: {fg}; padding: 24px; }}
  h1 {{ font-weight: 300; font-size: 1.4em; color: {sub_fg}; margin-bottom: 4px; }}
  .sub {{ color: {sub_fg}; font-size: 0.85em; }}
  h2 {{ font-weight: 400; font-size: 1.1em; color: #ccc; margin: 40px 0 4px; padding-bottom: 4px; border-bottom: 1px solid #333; }}
  .query-sub {{ font-size: 0.75em; color: {sub_fg}; margin: 0 0 16px; font-style: italic; }}
  .cluster {{ margin-bottom: 48px; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 12px; }}
  .photo-card {{ background: {card_bg}; border-radius: 8px; overflow: hidden; transition: background 0.2s; }}
  .photo-card:hover {{ background: {card_hover}; }}
  .photo-card a {{ text-decoration: none; color: inherit; display: block; }}
  .photo-card img {{ width: 100%; aspect-ratio: 3/2; object-fit: cover; display: block; background: #222; }}
  .photo-card .info {{ padding: 8px 10px 10px; }}
  .photo-card .filename {{ font-size: 0.75em; color: #aaa; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
  .photo-card .session-tag {{ font-size: 0.65em; color: #666; margin-top: 2px; }}
  .photo-card .score {{ font-size: 0.65em; margin-top: 2px; }}
  .photo-card.nodal {{ outline: 2px solid #ff9800; outline-offset: -2px; }}
  .photo-card.nodal .score {{ color: #ff9800; }}
  .photo-card.bisagra {{ outline: 1px solid #2196f3; outline-offset: -1px; }}
  .photo-card.bisagra .score {{ color: #2196f3; }}
  .nav {{ position: fixed; top: 12px; right: 24px; display: flex; flex-wrap: wrap; gap: 6px; max-width: 400px; justify-content: flex-end; }}
  .nav a {{ color: {sub_fg}; text-decoration: none; font-size: 0.7em; padding: 2px 6px; border-radius: 3px; background: {card_bg}; }}
  .nav a:hover {{ color: #ccc; background: {card_hover}; }}
</style>
</head>
<body>
<div class="nav">""")

    # Nav links
    for cg in concept_groups:
        anchor = escape(cg["titulo"].replace(" ", "-").lower())
        lines.append(f'<a href="#{anchor}">{escape(cg["emoji"])} {escape(cg["titulo"])}</a>')
    if nodals:
        lines.append('<a href="#nodal">⭐</a>')
    if bisagras:
        lines.append('<a href="#bisagra">🔗</a>')

    lines.append('</div>')

    # Header
    unique_count = len({p["path"] for p in all_photos})
    total_entries = len(all_photos)
    lines.append(f'<h1>{escape(title)}</h1>')
    lines.append(f'<p class="sub">{unique_count} fotos únicas · {total_entries} entradas · {len(queries)} conceptos</p>')

    # Concept clusters
    for cg in concept_groups:
        anchor = cg["titulo"].replace(" ", "-").lower()
        lines.append(f'<div class="cluster" id="{anchor}">')
        lines.append(f'  <h2>{cg["emoji"]} {escape(cg["titulo"])} — {len(cg["photos"])} resultados</h2>')
        lines.append(f'  <p class="query-sub">query: {escape(cg["query_text"])}</p>')
        lines.append('  <div class="grid">')

        for p in cg["photos"]:
            is_nodal = p["path"] in {n["path"] for n in nodals}
            is_bisagra = p["path"] in {b["path"] for b in bisagras}
            cls = "nodal" if is_nodal else ("bisagra" if is_bisagra else "")
            score_pct = f"{p['score']*100:.1f}%"
            lines.append(f'    <div class="photo-card {cls}">')
            lines.append(f'      <a href="file://{escape(p["path"])}" target="_blank">')
            lines.append(f'        <img src="file://{escape(p["path"])}" alt="{escape(p["filename"])}" loading="lazy">')
            lines.append('        <div class="info">')
            lines.append(f'          <div class="filename">{escape(p["filename"])}</div>')
            lines.append(f'          <div class="session-tag">{escape(p["session"])}</div>')
            lines.append(f'          <div class="score">{score_pct}</div>')
            lines.append('        </div>')
            lines.append('      </a>')
            lines.append('    </div>')

        lines.append('  </div>')
        lines.append('</div>')

    # Nodals (3+ clusters)
    nodals_shown = nodals[:max_nodal]
    if nodals_shown:
        lines.append('<div class="cluster" id="nodal">')
        lines.append(f'  <h2>⭐ Fotos nodales — aparecen en 3+ clusters</h2>')
        lines.append(f'  <p class="query-sub">{len(nodals)} fotos que conectan múltiples conceptos</p>')
        lines.append('  <div class="grid">')
        for n in nodals_shown:
            emoji_str = " ".join(sorted(n["emojis"]))
            lines.append(f'    <div class="photo-card nodal">')
            lines.append(f'      <a href="file://{escape(n["path"])}" target="_blank">')
            lines.append(f'        <img src="file://{escape(n["path"])}" alt="{escape(n["filename"])}" loading="lazy">')
            lines.append('        <div class="info">')
            lines.append(f'          <div class="filename">{escape(n["filename"])}</div>')
            lines.append(f'          <div class="session-tag">{escape(n["session"])}</div>')
            lines.append(f'          <div class="score">Clusters: {emoji_str}</div>')
            lines.append('        </div>')
            lines.append('      </a>')
            lines.append('    </div>')
        lines.append('  </div>')
        lines.append('</div>')

    # Bisagras (exactly 2 clusters)
    bisagras_shown = bisagras[:max_nodal]
    if bisagras_shown:
        lines.append('<div class="cluster" id="bisagra">')
        lines.append(f'  <h2>🔗 Fotos bisagra — aparecen en 2 clusters</h2>')
        lines.append(f'  <p class="query-sub">{len(bisagras)} fotos que conectan exactamente 2 conceptos</p>')
        lines.append('  <div class="grid">')
        for b in bisagras_shown:
            emoji_str = " ".join(sorted(b["emojis"]))
            lines.append(f'    <div class="photo-card bisagra">')
            lines.append(f'      <a href="file://{escape(b["path"])}" target="_blank">')
            lines.append(f'        <img src="file://{escape(b["path"])}" alt="{escape(b["filename"])}" loading="lazy">')
            lines.append('        <div class="info">')
            lines.append(f'          <div class="filename">{escape(b["filename"])}</div>')
            lines.append(f'          <div class="session-tag">{escape(b["session"])}</div>')
            lines.append(f'          <div class="score">Clusters: {emoji_str}</div>')
            lines.append('        </div>')
            lines.append('      </a>')
            lines.append('    </div>')
        lines.append('  </div>')
        lines.append('</div>')

    lines.append('</body>\n</html>')
    return "\n".join(lines)


def generate_map(
    queries_file: str,
    session: Optional[str] = None,
    project: Optional[str] = None,
    set_name: Optional[str] = None,
    variante: Optional[str] = None,
    color: Optional[str] = None,
    orientacion: Optional[str] = None,
    personajes: Optional[str] = None,
    n_results: int = 15,
    title: str = "Mapa conceptual",
    output: Optional[str] = None,
    output_dir: Optional[str] = None,
    db_path: str = "/media/dargonar/bkp_1t_new/photo_index",
    collection_name: str = "photos",
    model_name: str = "google/siglip-so400m-patch14-384",
    device: str = "auto",
    path_map: Optional[dict] = None,
    dark: bool = True,
    max_nodal: int = 10,
) -> str:
    """Run concept map generation.

    Returns path to generated HTML.
    """
    # Read queries
    with open(queries_file, "r", encoding="utf-8") as f:
        queries = json.load(f)

    if not queries:
        raise ValueError("El archivo de queries está vacío")

    # Connect ChromaDB
    client = chroma.get_client(db_path)
    collection = chroma.get_collection(client, collection_name, create=False)

    # Load model
    logger.info("🧠 Cargando modelo SigLIP...")
    model = SigLipModel(model_name, device=device)
    model.load()
    logger.info("✅ Modelo cargado")

    # Execute queries
    logger.info(f"🔍 Ejecutando {len(queries)} queries ({n_results} resultados c/u)...")
    all_photos = run_queries(
        queries, n_results, model, collection,
        path_map=path_map,
        session=session, project=project, set_name=set_name,
        variante=variante, color=color, orientacion=orientacion,
        personajes=personajes,
    )
    unique = len(set(p["path"] for p in all_photos))
    logger.info(f"   Total entradas: {len(all_photos)}")
    logger.info(f"   Fotos únicas: {unique}")

    # Generate HTML
    logger.info("📝 Generando HTML...")
    html = build_html(queries, all_photos, title=title, dark=dark, max_nodal=max_nodal)

    # Save
    if output:
        output_path = output
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    else:
        out_dir = output_dir or os.getcwd()
        output_path = next_filename(out_dir)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    logger.info(f"✅ Guardado: {output_path}")
    return output_path
