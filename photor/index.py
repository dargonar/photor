"""Index photos into ChromaDB with SigLIP embeddings and enriched metadata."""

import logging
import os
import json
from pathlib import Path
from typing import Optional

from PIL import Image, UnidentifiedImageError

from . import chroma
from .siglip import SigLipModel
from .utils import (
    find_images, extract_exif, extract_variante,
    detectar_orientacion, detectar_color,
)

logger = logging.getLogger("photor")


def index_photos(
    path: str,
    session: str,
    project: str = "",
    set_name: str = "default",
    personajes: str = "",
    tags: str = "",
    location: str = "",
    year: int = 0,
    rating: int = 0,
    selected: bool = False,
    description: str = "",
    db_path: str = "/media/dargonar/bkp_1t_new/photo_index",
    collection_name: str = "photos",
    model_name: str = "google/siglip-so400m-patch14-384",
    device: str = "auto",
    recursive: bool = False,
    include: Optional[str] = None,
    exclude: Optional[str] = None,
    dry_run: bool = False,
    overwrite: bool = False,
    extract_exif_flag: bool = True,
    extra_metadata: str = "",
    model: Optional["SigLipModel"] = None,  # pre-loaded model (avoids reload)
) -> dict:
    """Index photos into ChromaDB.

    Returns a dict with indexed, skipped, errors counts.
    """
    # Default project from session name
    if not project:
        project = session.split("-")[0]

    # Parse extra metadata
    extra_meta = {}
    if extra_metadata:
        try:
            extra_meta = json.loads(extra_metadata)
        except json.JSONDecodeError as e:
            logger.warning(f"Error parsing --metadata JSON: {e}")

    # Find images
    images = find_images(path, recursive=recursive, include=include, exclude=exclude)
    if not images:
        logger.warning(f"No se encontraron imágenes en: {path}")
        return {"indexed": 0, "skipped": 0, "errors": 0, "total": 0}

    logger.info(f"📸 Encontradas {len(images)} imágenes en '{path}'")
    logger.info(f"🗂️  Sesión: '{session}'   Proyecto: '{project}'   Set: '{set_name}'")
    if personajes:
        logger.info(f"👤 Personajes: {personajes}")
    if tags:
        logger.info(f"🏷️  Tags: {tags}")
    logger.info(f"💾 ChromaDB: {db_path}/{collection_name}")

    # Base metadata applied to all photos in this session
    base_metadata = {
        "session": session,
        "project": project,
        "set": set_name,
        "personajes": personajes,
        "tags": tags,
        "location": location,
        "description": description,
    }
    if year:
        base_metadata["year"] = year
    if rating:
        base_metadata["rating"] = rating
    if selected:
        base_metadata["selected"] = True

    if dry_run:
        logger.info("\n🔍 Dry-run — primeras 10 imágenes:")
        for img in images[:10]:
            logger.info(f"   · {img.name}")
        if len(images) > 10:
            logger.info(f"   ... y {len(images) - 10} más")
        logger.info(f"\n✅ Dry-run: {len(images)} imágenes listas para indexar")
        return {"indexed": 0, "skipped": 0, "errors": 0, "total": len(images)}

    # Load model (or use pre-loaded one)
    if model is not None:
        siglip_model = model
    else:
        siglip_model = SigLipModel(model_name, device=device)
        siglip_model.load()

    # Open ChromaDB
    client = chroma.get_client(db_path)
    collection = chroma.get_collection(client, collection_name)

    # Index
    indexed = 0
    skipped = 0
    errors = 0

    for img_path in images:
        img_id = f"{session}/{img_path.name}"

        # Check if already indexed
        if not overwrite:
            existing = collection.get(ids=[img_id])
            if existing and existing["ids"]:
                logger.info(f"   ⏭️  Ya indexado: {img_path.name}")
                skipped += 1
                continue

        try:
            image = Image.open(img_path).convert("RGB")
        except (UnidentifiedImageError, OSError) as e:
            logger.warning(f"   ❌ No se pudo abrir: {img_path.name} — {e}")
            errors += 1
            continue

        try:
            # Embedding
            embedding = siglip_model.encode_image(image)

            # Auto-detect metadata
            variante = extract_variante(img_path.name)
            orientacion = detectar_orientacion(image)
            color = detectar_color(image)

            # EXIF
            exif = {}
            if extract_exif_flag:
                exif = extract_exif(img_path)

            # Build metadata
            metadata = {
                **base_metadata,
                **extra_meta,
                "variante": variante,
                "orientacion": orientacion,
                "color": color,
                "fecha": exif.get("fecha", ""),
                "camara": exif.get("camara", ""),
                "lente": exif.get("lente", ""),
                "focal": exif.get("focal", 0),
                "iso": exif.get("iso", 0),
                "apertura": exif.get("apertura", 0.0),
                "velocidad": str(exif.get("velocidad", "")),
                "flash": exif.get("flash", False),
                "filename": img_path.name,
                "path": str(img_path.absolute()),
                "format": img_path.suffix.lower().lstrip("."),
            }

            # Clean up None/empty values from metadata
            metadata = {k: v for k, v in metadata.items() if v is not None and v != ""}

            if overwrite:
                # Delete existing first
                existing = collection.get(ids=[img_id])
                if existing and existing["ids"]:
                    collection.delete(ids=[img_id])

            collection.add(
                ids=[img_id],
                embeddings=[embedding],
                metadatas=[metadata],
                documents=[img_path.name],
            )

            info_parts = [
                f"✅ {img_path.name}",
                f"{project}/{set_name}",
                variante,
                color,
                orientacion,
            ]
            if exif.get("camara"):
                info_parts.append(exif["camara"])
            logger.info(f"   {' | '.join(p for p in info_parts if p)}")
            indexed += 1

        except Exception as e:
            logger.warning(f"   ❌ Error con {img_path.name}: {e}")
            errors += 1

    logger.info("")
    logger.info("═══════════════════════════════════════")
    logger.info(f"  📊 Resumen:")
    logger.info(f"     Indexados: {indexed}")
    logger.info(f"     Saltados (ya existían): {skipped}")
    logger.info(f"     Errores: {errors}")
    logger.info(f"     Total en carpeta: {len(images)}")
    logger.info("═══════════════════════════════════════")

    return {
        "indexed": indexed,
        "skipped": skipped,
        "errors": errors,
        "total": len(images),
    }
