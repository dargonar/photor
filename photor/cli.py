"""photor CLI — typer entry point."""

import logging
import sys
from typing import Optional

import typer

from . import __version__
from .utils import load_config
from . import index as index_mod
from . import search as search_mod
from . import map_generator as map_mod
from .discover import discover_sessions, print_discovery
from .serve import serve as serve_fn

# ── Global config ───────────────────────────────────────────────────
_cfg = load_config()


def _db():
    return _cfg.get("chroma", {}).get("path", "/media/dargonar/bkp_1t_new/photo_index")


def _collection():
    return _cfg.get("chroma", {}).get("collection", "photos")


def _model():
    return _cfg.get("model", {}).get("name", "google/siglip-so400m-patch14-384")


def _device():
    return _cfg.get("model", {}).get("device", "auto")


def _n_results():
    return _cfg.get("search", {}).get("n_results", 10)


# ── Logging ─────────────────────────────────────────────────────────

def _setup_logging(verbose: bool = False):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(message)s",
        stream=sys.stdout,
    )


app = typer.Typer(
    name="photor",
    help="📷 CLI para workflow fotográfico: indexar, buscar, raw2jpg, crop, resize, mapas conceptuales",
    no_args_is_help=True,
)


# ═════════════════════════════════════════════════════════════════════
# COMMANDS
# ═════════════════════════════════════════════════════════════════════

# ── search ─────────────────────────────────────────────────────────

@app.command()
def search(
    query: str = typer.Argument("", help="Texto de búsqueda"),
    session: str = typer.Option("", "--session", "-s", help="Filtrar por sesión"),
    n: int = typer.Option(_n_results(), "-n", help="Número de resultados"),
    db: str = typer.Option(_db(), "--db", help="ChromaDB path"),
    collection: str = typer.Option(_collection(), "--collection", help="Nombre de colección"),
    model: str = typer.Option(_model(), "--model", help="Modelo de embeddings"),
    device: str = typer.Option(_device(), "--device", help="auto | cuda | cpu"),
    sessions: bool = typer.Option(False, "--sessions", help="Listar sesiones indexadas"),
    stats: bool = typer.Option(False, "--stats", help="Mostrar estadísticas"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Output detallado"),
):
    """Buscar fotos por concepto visual. Usá --sessions o --stats para listar."""
    _setup_logging(verbose)

    if sessions:
        search_mod.list_sessions(db, collection)
        return

    if stats:
        search_mod.show_stats(db, collection)
        return

    if not query:
        typer.echo("photor search: requiere texto de búsqueda.")
        typer.echo("  Usá --sessions para listar sesiones o --stats para ver estadísticas.")
        raise typer.Exit(code=1)

    session_filter = session if session else None

    results = search_mod.search_photos(
        query=query,
        session=session_filter,
        n_results=n,
        db_path=db,
        collection_name=collection,
        model_name=model,
        device=device,
    )

    search_mod.print_search_results(results)


# ── index ──────────────────────────────────────────────────────────

@app.command()
def index(
    path: str = typer.Argument(..., help="Ruta a carpeta o archivo con fotos"),
    session: str = typer.Option("", "--session", "-s", help="Nombre de la sesión. Si se omite con --recursive, se auto-detecta."),
    # Metadata flags
    project: str = typer.Option("", "--project", help="Nombre del proyecto (agrupa sesiones)"),
    set_name: str = typer.Option("default", "--set", help="Subcategoría: portfolio, raw, alternative, chosen, descartes"),
    personajes: str = typer.Option("", "--personajes", help="Personajes separados por coma"),
    tags: str = typer.Option("", "--tags", help="Tags libres separados por coma"),
    location: str = typer.Option("", "--location", help="Ubicación general de la sesión"),
    year: int = typer.Option(0, "--year", help="Año de la sesión"),
    rating: int = typer.Option(0, "--rating", help="Rating 1-5"),
    selected: bool = typer.Option(False, "--selected", help="Marcar como selección editorial"),
    description: str = typer.Option("", "--description", help="Descripción general de la sesión"),
    extra_metadata: str = typer.Option("", "--metadata", help="JSON extra para metadata custom"),
    # Behavior flags
    db: str = typer.Option(_db(), "--db", help="ChromaDB path"),
    collection: str = typer.Option(_collection(), "--collection", help="Nombre de colección"),
    model: str = typer.Option(_model(), "--model", help="Modelo de embeddings"),
    device: str = typer.Option(_device(), "--device", help="auto | cuda | cpu"),
    recursive: bool = typer.Option(False, "--recursive", "-r", help="Escanear subdirectorios"),
    include: str = typer.Option("", "--include", help="Glob de inclusión (ej: *.jpg,*.png)"),
    exclude: str = typer.Option("", "--exclude", help="Glob de exclusión (ej: *thumb*)"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Solo mostrar qué se indexaría"),
    overwrite: bool = typer.Option(False, "--overwrite", help="Re-indexar aunque ya exista"),
    no_exif: bool = typer.Option(False, "--no-exif", help="No extraer EXIF automático"),
    reset: bool = typer.Option(False, "--reset", help="Eliminar colección y salir"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Output detallado"),
):
    """Indexar fotos en ChromaDB con metadata enriquecida."""
    _setup_logging(verbose)

    if reset:
        from .chroma import reset_collection
        ok = reset_collection(db, collection)
        if ok:
            typer.echo(f"🗑️  Colección '{collection}' eliminada. Ahora indexá con --path --session")
        else:
            typer.echo(f"⚠️  Colección '{collection}' no existía.")
        raise typer.Exit()

    if not session and not recursive:
        typer.echo("❌ Requiere --session (nombre de la sesión), o --recursive para auto-detección")
        raise typer.Exit(code=1)

    # ── Recursive auto-discovery mode ──────────────────────────────
    if recursive and not session:
        from pathlib import Path
        from .discover import discover_sessions
        root = Path(path).expanduser().resolve()
        if not root.exists():
            typer.echo(f"❌ Ruta no existe: {root}")
            raise typer.Exit(code=1)

        discovered = discover_sessions(root, recursive=True)
        if not discovered:
            typer.echo("📂 No se encontraron sesiones para indexar.")
            raise typer.Exit()

        typer.echo(f"📂 Indexando {len(discovered)} sesiones descubiertas:\n")
        # Load model ONCE before the loop
        from .siglip import SigLipModel
        typer.echo("🧠 Cargando modelo SigLIP...")
        siglip_model = SigLipModel(model_name=model, device=device)
        siglip_model.load()
        typer.echo("✅ Modelo cargado\n")
        total_ok = 0
        total_err = 0
        for s in discovered:
            meta = s["config"] if s["config"] else {}
            s_name = meta.get("session", s["session"])
            p_name = meta.get("project", s.get("project", ""))
            set_n = meta.get("set", s.get("set", "default"))

            typer.echo(f"  ── {s_name} ({set_n}) ──")
            result = index_mod.index_photos(
                path=s["path"],
                session=s_name,
                project=p_name or s_name.split("-")[0],
                set_name=set_n,
                personajes=meta.get("personajes", personajes or ""),
                tags=meta.get("tags", tags or ""),
                location=meta.get("location", location or ""),
                year=meta.get("year", year or 0),
                rating=meta.get("rating", rating or 0),
                selected=meta.get("selected", selected or False),
                description=meta.get("description", description or ""),
                db_path=db,
                collection_name=collection,
                model_name=model,
                device=device,
                recursive=False,  # per-session is flat
                dry_run=dry_run,
                overwrite=overwrite,
                extract_exif_flag=not no_exif,
                extra_metadata=extra_metadata,
                model=siglip_model,  # reuse pre-loaded model
            )
            total_ok += result["indexed"]
            total_err += result["errors"]
            typer.echo("")

        typer.echo("═══════════════════════════════════════")
        typer.echo(f"  📊 Total indexado: {total_ok}  |  Errores: {total_err}")
        typer.echo("═══════════════════════════════════════")
        if total_err > 0:
            raise typer.Exit(code=1)
        return

    # ── Single session mode ─────────────────────────────────────
    result = index_mod.index_photos(
        path=path,
        session=session,
        project=project,
        set_name=set_name,
        personajes=personajes,
        tags=tags,
        location=location,
        year=year,
        rating=rating,
        selected=selected,
        description=description,
        db_path=db,
        collection_name=collection,
        model_name=model,
        device=device,
        recursive=recursive,
        include=include if include else None,
        exclude=exclude if exclude else None,
        dry_run=dry_run,
        overwrite=overwrite,
        extract_exif_flag=not no_exif,
        extra_metadata=extra_metadata,
    )

    if result["errors"] > 0:
        raise typer.Exit(code=1)


# ── raw2jpg (placeholder) ──────────────────────────────────────────

@app.command()
def raw2jpg():
    """Convertir RAW (ARW, CR2, NEF, DNG) a JPEG. (Fase 2)"""
    typer.echo("⚠️  Comando raw2jpg aún no implementado (Fase 2)")
    raise typer.Exit(code=1)


# ── crop (placeholder) ─────────────────────────────────────────────

@app.command()
def crop():
    """Recortar bandas blancas de fotos Instagram. (Fase 3)"""
    typer.echo("⚠️  Comando crop aún no implementado (Fase 3)")
    raise typer.Exit(code=1)


# ── resize (placeholder) ───────────────────────────────────────────

@app.command()
def resize():
    """Redimensionar y copiar fotos recursivamente. (Fase 4)"""
    typer.echo("⚠️  Comando resize aún no implementado (Fase 4)")
    raise typer.Exit(code=1)


# ── map ──────────────────────────────────────────────────────────────

@app.command()
def map(
    queries_file: str = typer.Argument(..., help="Archivo JSON con queries conceptuales"),
    session: str = typer.Option("", "--session", "-s", help="Filtrar por sesión"),
    project: str = typer.Option("", "--project", help="Filtrar por proyecto"),
    set_name: str = typer.Option("", "--set", help="Filtrar por set (portfolio, raw...)"),
    variante: str = typer.Option("", "--variante", help="Filtrar por variante (v2, pop, moody...)"),
    color: str = typer.Option("", "--color", help="Filtrar color|bw"),
    orientacion: str = typer.Option("", "--orientacion", help="Filtrar horizontal|vertical|cuadrada"),
    personajes: str = typer.Option("", "--personajes", help="Filtrar por personajes"),
    n: int = typer.Option(_cfg.get("map", {}).get("n_results", 15), "-n", help="Resultados por concepto"),
    title: str = typer.Option("Mapa conceptual", "--title", help="Título del HTML"),
    output: str = typer.Option("", "--output", "-o", help="Path de salida específico"),
    output_dir: str = typer.Option(_cfg.get("map", {}).get("output_dir", ""), "--output-dir", help="Directorio para auto-incremental"),
    db: str = typer.Option(_db(), "--db", help="ChromaDB path"),
    collection: str = typer.Option(_collection(), "--collection", help="Nombre de colección"),
    model: str = typer.Option(_model(), "--model", help="Modelo de embeddings"),
    device: str = typer.Option(_device(), "--device", help="auto|cuda|cpu"),
    path_map_json: str = typer.Option("", "--path-map", help="JSON con reemplazos de path: {'/old/':'/new/'}"),
    dark: bool = typer.Option(True, "--dark/--light", help="Tema oscuro/claro"),
    nodal_top: int = typer.Option(10, "--nodal-top", help="Máx fotos nodales a mostrar"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Output detallado"),
):
    """Generar mapa conceptual HTML desde queries semánticas.

    Ejemplos:
        photor map queries.json
        photor map queries.json -s brenda-pileta-kinky -n 20
        photor map queries.json --project brenda --color bw -o mapa.html
    """
    import logging
    _setup_logging(verbose)
    logging.getLogger("photor").setLevel(logging.DEBUG if verbose else logging.INFO)

    # Parse path map
    path_map = None
    if path_map_json:
        import json
        path_map = json.loads(path_map_json)

    try:
        result = map_mod.generate_map(
            queries_file=queries_file,
            session=session or None,
            project=project or None,
            set_name=set_name or None,
            variante=variante or None,
            color=color or None,
            orientacion=orientacion or None,
            personajes=personajes or None,
            n_results=n,
            title=title,
            output=output or None,
            output_dir=output_dir or None,
            db_path=db,
            collection_name=collection,
            model_name=model,
            device=device,
            path_map=path_map,
            dark=dark,
            max_nodal=nodal_top,
        )
        typer.echo(f"\n🔗 Abrí el archivo en el navegador:\n   file://{result}")
    except Exception as e:
        typer.echo(f"❌ Error: {e}", err=True)
        raise typer.Exit(code=1)


# ── serve ───────────────────────────────────────────────────────

@app.command()
def serve(
    port: int = typer.Option(9000, "--port", "-p", help="Puerto del servidor web"),
    host: str = typer.Option("0.0.0.0", "--host", help="Host del servidor web"),
):
    """Iniciar Web UI para mapas conceptuales.

    Abre un servidor web con interfaz gráfica para explorar
    conceptos visuales. No carga SigLIP — delega al CLI.

    Ejemplo:
        photor serve --port 9000
    """
    serve_fn(host=host, port=port)


# ── discover ────────────────────────────────────────────────────────

@app.command()
def discover(
    path: str = typer.Argument(".", help="Ruta a explorar"),
    recursive: bool = typer.Option(True, "--recursive", "-r", help="Explorar subdirectorios"),
):
    """Descubrir sesiones indexables en una estructura de directorios.

    Muestra qué sesiones detectaría el indexador con auto-detección,
    incluyendo photor.yaml si existe en cada carpeta.
    """
    from pathlib import Path
    root = Path(path).expanduser().resolve()
    if not root.exists():
        typer.echo(f"❌ Ruta no existe: {root}")
        raise typer.Exit(code=1)

    sessions = discover_sessions(root, recursive=recursive)
    print_discovery(sessions)


# ── version callback ───────────────────────────────────────────────

@app.callback()
def version_callback(
    version: bool = typer.Option(False, "--version", help="Mostrar versión"),
):
    if version:
        typer.echo(f"photor v{__version__}")
        raise typer.Exit()


if __name__ == "__main__":
    app()