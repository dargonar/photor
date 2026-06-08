#!/usr/bin/env python3
"""
Add original_location to all photor.session.yaml files.
For dirs without YAML: freeze inherited metadata + add original_location + set=dirname.
"""

import sys
import yaml
from pathlib import Path

sys.path.insert(0, '/media/dargonar/bkp_1t_new/portfolio/wdir/photor')
from photor.discover import resolve_session_metadata, slugify
from photor.utils import find_images, VALID_EXTENSIONS

BASE = Path("/media/dargonar/bkp_1t_new/portfolio/photos")
FNAME = "photor.session.yaml"
SET_DIRS = {"raw", "alternative", "chosen", "descartes", "portfolio", "variantes",
            "sq", "ig_ready", "re_edit", "editadas", "mobile", "edited", "instagram",
            "instagram-square", "selected"}


def has_photos(d):
    valid_lower = {e.lower() for e in VALID_EXTENSIONS}
    return any(f.suffix.lower() in valid_lower for f in d.iterdir() if f.is_file())


def walk_all(directory):
    """Walk all directories and find those with photos."""
    if directory.name.startswith('.'):
        return []
    results = []
    if has_photos(directory):
        results.append(directory)
    for child in sorted(directory.iterdir()):
        if child.is_dir() and not child.name.startswith('.'):
            results.extend(walk_all(child))
    return results


# ── Phase 1: Add original_location to existing YAMLs ──

print("=== FASE 1: Agregando original_location a YAMLs existentes ===")
count_existing = 0
for yaml_file in sorted(BASE.rglob(FNAME)):
    with open(yaml_file) as f:
        data = yaml.safe_load(f) or {}

    if 'original_location' in data:
        continue  # already has it

    data['original_location'] = ''
    with open(yaml_file, 'w') as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
    print(f"  ✅ {yaml_file.relative_to(BASE)}")
    count_existing += 1

print(f"  → {count_existing} actualizados\n")


# ── Phase 2: Create YAML for dirs without one ──

print("=== FASE 2: Creando YAML para carpetas sin metadata ===")
count_new = 0
for dir_path in walk_all(BASE):
    yaml_path = dir_path / FNAME
    if yaml_path.exists():
        continue  # already handled in phase 1

    # Resolve current inherited metadata
    meta = resolve_session_metadata(dir_path)
    dir_name = dir_path.name

    # Build new YAML: freeze inherited fields + add original_location + override set
    new_data = {}

    # Fields to freeze from inheritance (all except set/selected/rating)
    for field in ['session', 'project', 'personajes', 'tags', 'location', 'year', 'description']:
        val = meta.get(field)
        if val:
            new_data[field] = val

    # Add original_location
    new_data['original_location'] = ''

    # Set = directory name (user's request)
    new_data['set'] = dir_name.lower().replace(' ', '-').replace('_', '-')

    # Ensure session exists (use slugified dirname as fallback)
    if 'session' not in new_data:
        new_data['session'] = slugify(dir_name)

    with open(yaml_path, 'w') as f:
        yaml.dump(new_data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
    print(f"  ✅ CREADO: {dir_path.relative_to(BASE)}/")
    print(f"     session: {new_data.get('session', '?')} | set: {new_data['set']}")
    if new_data.get('project'):
        print(f"     project: {new_data['project']}")
    if new_data.get('personajes'):
        print(f"     personajes: {new_data['personajes']}")
    count_new += 1

print(f"\n  → {count_new} creados\n")
print(f"📝 Total: {count_existing} actualizados + {count_new} creados")
