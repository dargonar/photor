"""Shared utilities for photor CLI."""

import os
import re
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from PIL import Image, ExifTags
from PIL.ExifTags import TAGS


# ── Config ──────────────────────────────────────────────────────────

DEFAULT_DB = "/media/dargonar/bkp_1t_new/photo_index"
DEFAULT_MODEL = "google/siglip-so400m-patch14-384"
DEFAULT_COLLECTION = "photos"

VALID_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff", ".tif",
    ".JPG", ".JPEG", ".PNG", ".WEBP", ".BMP", ".TIFF", ".TIF",
}

VALID_RAW_EXTENSIONS = {".arw", ".cr2", ".nef", ".dng", ".raf", ".rw2"}


# ── File helpers ────────────────────────────────────────────────────

def find_images(path: str, recursive: bool = False,
                include: Optional[str] = None,
                exclude: Optional[str] = None) -> list[Path]:
    """Find image files in path. Supports glob include/exclude."""
    p = Path(path)
    images = []

    if p.is_file():
        if p.suffix.lower() in {e.lower() for e in VALID_EXTENSIONS}:
            images.append(p)
        return images

    pattern = "**/*" if recursive else "*"
    for f in sorted(p.glob(pattern)):
        if not f.is_file():
            continue
        if f.suffix.lower() not in {e.lower() for e in VALID_EXTENSIONS}:
            continue
        if include and not any(f.match(g) for g in include.split(",")):
            continue
        if exclude and any(f.match(g) for g in exclude.split(",")):
            continue
        images.append(f)

    return images


def find_raw_files(path: str, recursive: bool = False) -> list[Path]:
    """Find RAW files (ARW, CR2, etc.) in path."""
    p = Path(path)
    raw_files = []

    if p.is_file():
        if p.suffix.lower() in VALID_RAW_EXTENSIONS:
            raw_files.append(p)
        return raw_files

    pattern = "**/*" if recursive else "*"
    for f in sorted(p.glob(pattern)):
        if f.is_file() and f.suffix.lower() in VALID_RAW_EXTENSIONS:
            raw_files.append(f)

    return raw_files


# ── EXIF extraction ─────────────────────────────────────────────────

EXIF_FIELDS = {
    "DateTimeOriginal": "fecha",
    "Make": "camara_make",
    "Model": "camara",
    "ISOSpeedRatings": "iso",
    "FNumber": "apertura",
    "ExposureTime": "velocidad",
    "FocalLength": "focal",
    "LensModel": "lente",
    "FocalLengthIn35mmFilm": "focal_35mm",
    "Flash": "flash",
    "ExposureBiasValue": "exposure_bias",
    "ExposureProgram": "exposure_program",
    "WhiteBalance": "white_balance",
    "GPSInfo": "gps_info",
}


def extract_exif(img_path: Path) -> dict:
    """Extract EXIF metadata from an image file."""
    exif_data = {}
    try:
        img = Image.open(img_path)
        exif_raw = img._getexif()
        if exif_raw:
            for tag_id, value in exif_raw.items():
                tag_name = TAGS.get(tag_id, tag_id)
                mapped = EXIF_FIELDS.get(tag_name)
                if mapped:
                    # Normalize types for ChromaDB (no lists, no dicts)
                    if isinstance(value, tuple):
                        if mapped == "flash":
                            value = bool(value[0]) if value else False
                        else:
                            continue  # skip complex EXIF tuples
                    elif isinstance(value, bytes):
                        try:
                            value = value.decode("utf-8", errors="replace")
                        except Exception:
                            continue
                    elif tag_name == "FNumber":
                        try:
                            value = float(value)
                        except (TypeError, ValueError):
                            continue
                    elif tag_name == "FocalLength":
                        try:
                            value = float(value)
                        except (TypeError, ValueError):
                            continue
                    exif_data[mapped] = value
    except Exception:
        pass

    # Fallback: file modification time
    if "fecha" not in exif_data:
        mtime = os.path.getmtime(img_path)
        exif_data["fecha"] = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d")
    else:
        # Normalize "YYYY:MM:DD HH:MM:SS" → "YYYY-MM-DD"
        fecha = str(exif_data["fecha"]).replace(":", "-", 2).split(" ")[0]
        exif_data["fecha"] = fecha

    # Unify camera name
    if "camara" not in exif_data and "camara_make" in exif_data:
        exif_data["camara"] = exif_data.pop("camara_make")

    # Normalize flash
    if "flash" in exif_data:
        exif_data["flash"] = bool(exif_data["flash"])

    return exif_data


# ── Image analysis ──────────────────────────────────────────────────

def extract_variante(filename: str) -> str:
    """Extract edit variant from filename.

    IMG_0089.jpg        → original
    IMG_0729_v2.jpg     → v2
    IMG_1488_pop.jpg    → pop
    IMG_1508_moody_pop.jpg → moody_pop
    """
    name = Path(filename).stem
    match = re.match(r'^[A-Za-z]+_\d+(?:-\d+)?(?:_(.+))?$', name)
    if match and match.group(1):
        return match.group(1)
    return "original"


def detectar_orientacion(img: Image.Image) -> str:
    """Detect orientation from image dimensions."""
    w, h = img.size
    if w > h:
        return "horizontal"
    elif h > w:
        return "vertical"
    return "cuadrada"


def detectar_color(img: Image.Image) -> str:
    """Detect if image is color or B&W via channel variance."""
    if img.mode in ("L", "1"):
        return "bw"
    if img.mode in ("RGB", "RGBA"):
        w, h = img.size
        if w < 10 or h < 10:
            return "color"
        small = img.resize((32, 32))
        pixels = list(small.getdata())
        total_var = 0
        count = 0
        for p in pixels:
            if len(p) >= 3:
                r, g, b = p[0], p[1], p[2]
                avg = (r + g + b) / 3.0
                total_var += abs(r - avg) + abs(g - avg) + abs(b - avg)
                count += 1
        avg_var = total_var / count if count > 0 else 0
        return "bw" if avg_var < 10 else "color"
    return "color"


# ── Config loading ──────────────────────────────────────────────────

def load_config(config_path: str | None = None) -> dict:
    """Load photor.yaml config, with file overrides."""
    default_config = {
        "chroma": {"path": DEFAULT_DB, "collection": DEFAULT_COLLECTION},
        "model": {"name": DEFAULT_MODEL, "device": "auto"},
        "search": {"n_results": 10},
        "raw2jpg": {"quality": 95, "camera_wb": True, "half_size": False,
                     "output_bps": 8, "skip_existing": True, "format": "jpg"},
        "crop": {"threshold": 240, "purity": 0.95, "max_size": 1920,
                 "max_bytes": 2 * 1024 * 1024, "format": "jpg"},
        "resize": {"max_size": 1920, "quality": 95,
                    "max_bytes": 2 * 1024 * 1024, "method": "binary", "format": "jpg"},
        "map": {"n_results": 15, "dark": True, "inline": True,
                "output_dir": "/media/dargonar/bkp_1t_new/portfolio/wdir"},
    }

    if config_path is None:
        candidates = [
            "photor.yaml",
            os.path.join(os.path.dirname(__file__), "..", "photor.yaml"),
            os.path.expanduser("~/.config/photor.yaml"),
        ]
    else:
        candidates = [config_path]

    for path in candidates:
        p = Path(path).expanduser().resolve()
        if p.exists():
            try:
                import yaml
                with open(p) as f:
                    user_config = yaml.safe_load(f) or {}
                # Deep merge
                merged = default_config.copy()
                for section, values in user_config.items():
                    if section in merged and isinstance(merged[section], dict):
                        merged[section].update(values)
                    else:
                        merged[section] = values
                merged["_config_path"] = str(p)
                return merged
            except Exception:
                pass

    return default_config


# ── Path formatting ─────────────────────────────────────────────────

def media_path(path: str | Path) -> str:
    """Format path for Hermes WebUI inline display."""
    return f"MEDIA:{path}"


def format_size(bytes_: int) -> str:
    """Human-readable file size."""
    for unit in ("B", "KB", "MB", "GB"):
        if bytes_ < 1024:
            return f"{bytes_:.1f} {unit}"
        bytes_ /= 1024
    return f"{bytes_:.1f} TB"
