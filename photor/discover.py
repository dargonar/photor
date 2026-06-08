"""Discover sessions in a directory tree for batch indexing."""

import os
import yaml
from pathlib import Path
from typing import Optional

from .utils import find_images


# ── Known set subdirectory names ────────────────────────────────────

SET_NAMES = {"raw", "alternative", "chosen", "descartes", "portfolio", "variantes", "selection", "edited"}

# Container directories that should never be treated as projects
CONTAINER_NAMES = {"photos", "images", "portfolio", "fotos", "foto", "img", "pics", "gallery"}

FNAME = "photor.session.yaml"


def discover_photor_yaml(directory: Path) -> Optional[dict]:
    """Look for photor.session.yaml in a directory. Returns parsed dict or None."""
    path = directory / FNAME
    if path.exists():
        try:
            with open(path) as f:
                return yaml.safe_load(f) or {}
        except Exception:
            pass
    return None


def walk_up_photor_yaml(directory: Path) -> Optional[dict]:
    """Walk up the tree looking for the nearest photor.session.yaml.

    Returns (inherited_metadata, depth) or None.
    Walks parent → grandparent → great-grandparent.
    Stops at CONTAINER_NAMES or filesystem root.
    """
    current = directory.parent
    depth = 1
    while current and current.exists() and current.name not in CONTAINER_NAMES:
        data = discover_photor_yaml(current)
        if data:
            return data, depth
        current = current.parent
        depth += 1
    return None


def inherit_metadata(ancestor_data: dict, dir_name: str, depth: int) -> dict:
    """Inherit metadata from ancestor, applying exceptions for child dirs.

    - All fields inherited except:
      - set → forced to dir_name (lowercase)
      - selected → forced to False
      - rating → never inherited
    - session and project are inherited from ancestor
    """
    if ancestor_data is None:
        return {}

    inherited = dict(ancestor_data)

    # Remove blacklisted fields
    inherited.pop("rating", None)
    inherited.pop("selected", None)

    # Force set = directory name
    inherited["set"] = dir_name.lower().replace(" ", "-").replace("_", "-")

    # Don't inherit session name from arbitrary depth — only from parent
    # Actually, the user said "hereda todo de la carpeta padre, o de la carpeta abuela"
    # So session IS inherited, but maybe we should only inherit session from parent (depth=1)
    # Let's keep session inheritance for now, it's what the user wants

    return inherited


def resolve_session_metadata(directory: Path) -> dict:
    """Resolve metadata for a directory using inheritance chain.

    1. Check if directory has its own photor.session.yaml → use it
    2. If not, walk up to parent/grandparent looking for one → inherit with exceptions
    3. If none found, fall back to auto-detection

    Returns dict with at minimum: session, set
    """
    # Step 1: own yaml
    own = discover_photor_yaml(directory)
    if own:
        return own

    # Step 2: inherit from ancestor
    ancestor = walk_up_photor_yaml(directory)
    if ancestor:
        data, depth = ancestor
        dir_name = directory.name
        inherited = inherit_metadata(data, dir_name, depth)
        inherited["session"] = data.get("session", slugify(directory.name))
        inherited["project"] = data.get("project", "")
        # Mark as inherited (not from own yaml)
        inherited["_inherited"] = True
        # Pass through selected/rating from the ancestor only if not blacklisted
        # Actually the inherit_metadata already strips them
        return inherited

    # Step 3: auto-detect
    return auto_detect_session(directory)


def detect_set_from_path(dir_name: str) -> str:
    """Detect set name from directory name (raw, alternative, etc.)."""
    name = dir_name.lower().replace("-", "_").replace(" ", "_")
    if name in SET_NAMES:
        return name
    return "default"


def slugify(name: str) -> str:
    """Convert a directory name to a session/project slug."""
    return name.lower().replace("_", "-").replace(" ", "-").replace("--", "-")


def auto_detect_session(directory: Path) -> dict:
    """
    Auto-detect session metadata from directory path structure.
    Last-resort fallback when no photor.session.yaml exists up the tree.

    Returns dict with session, project, set keys.
    """
    dir_name = directory.name
    parent = directory.parent

    detected_set = detect_set_from_path(dir_name)

    if detected_set != "default":
        session_name = slugify(parent.name)
        return {
            "session": session_name,
            "project": slugify(parent.name),
            "set": detected_set,
        }
    else:
        session_name = slugify(dir_name)
        project = ""
        if parent and parent.exists() and parent.name not in CONTAINER_NAMES:
            siblings = [
                d for d in parent.iterdir()
                if d.is_dir() and d.name not in SET_NAMES
                and d.name not in CONTAINER_NAMES
                and d.name != dir_name
            ]
            has_set_subdirs = any(
                (directory / s).is_dir() for s in SET_NAMES
            )
            if len(siblings) >= 1 or has_set_subdirs:
                project = slugify(parent.name)

        return {
            "session": session_name,
            "project": project,
            "set": "default",
            "_auto_detected": True,
        }


def discover_sessions(root: Path, recursive: bool = False) -> list[dict]:
    """
    Walk a directory tree and discover all indexable sessions.

    Walks ALL directories at ANY depth. Each directory with photos
    is a session (uses its own photor.session.yaml or inherits).

    Returns list of dicts with path, session, project, set, config, images.
    """
    sessions = []

    if not root.is_dir():
        return sessions

    def walk(directory: Path):
        if directory.name.startswith("."):
            return
        images = find_images(str(directory), recursive=False)
        if images:
            metadata = resolve_session_metadata(directory)
            is_own = not metadata.get("_inherited") and not metadata.get("_auto_detected")
            sessions.append({
                "path": str(directory),
                "session": metadata.get("session", slugify(directory.name)),
                "project": metadata.get("project", ""),
                "set": metadata.get("set", "default"),
                "config": metadata if is_own else {},
                "images": images,
            })
        if recursive:
            for child in sorted(directory.iterdir()):
                if child.is_dir():
                    walk(child)

    walk(root)
    return sessions


def print_discovery(sessions: list[dict]):
    """Print discovered sessions in a readable format."""
    if not sessions:
        print("📂 No se encontraron sesiones para indexar")
        return

    print(f"📂 Descubiertas {len(sessions)} sesiones:\n")
    for s in sessions:
        parts = [
            f"  📁 {s['path']}",
            f"     Sesión: {s['session']}",
        ]
        if s["project"]:
            parts.append(f"     Proyecto: {s['project']}")
        parts.append(f"     Set: {s['set']}")
        parts.append(f"     Fotos: {len(s['images'])}")
        if s["config"]:
            parts.append(f"     📝 photor.session.yaml: sí")
        print(" | ".join(parts))
        print()
