# `photor` — Functional Specification v1

## 1. Overview

`photor` is a unified CLI tool for the complete photography workflow: from RAW conversion to semantic search to curatorial mapping. All subcommands share a common config, path conventions, and ChromaDB backend.

**Install location:** `/media/dargonar/bkp_1t_new/portfolio/wdir/photor/`
**Entry point:** `photor` (Python, installed with pip or run via `python3 -m photor`)

---

## 2. Global defaults

| Config | Default | Flag |
|--------|---------|------|
| ChromaDB path | `/media/dargonar/bkp_1t_new/photo_index/` | `--db` |
| Collection name | `photos` | `--collection` |
| Model | `google/siglip-so400m-patch14-384` | `--model` |
| Default results | `10` | `-n` or `--n` |
| JPEG quality | `95` | `--quality` |
| Max dimension | `1920` | `--max-size` |
| Max file size | `2 MB` | `--max-bytes` |
| Dry-run | `off` | `--dry-run` or `-n` for search |

---

## 3. Commands

### 3.1 `photor index`

Index photos into ChromaDB using SigLIP embeddings. Extrae EXIF metadata automáticamente (cámara, lente, ISO, apertura, fecha) y detecta orientación, color/B&W y variante de edición desde el nombre del archivo.

```
photor index <path> --session <name> [options]
```

**Arguments:**
- `path` — folder or file path (positional, required)
- `--session`, `-s` — session name (required)

#### Metadata flags (guardados en ChromaDB como filtros)

| Flag | Tipo | Default | Descripción |
|------|------|---------|-------------|
| `--project` | string | 1er palabra del session | Proyecto padre (agrupa sesiones). Ej: `brenda`, `mila`, `andy` |
| `--set` | string | `"default"` | Subcategoría dentro del proyecto: `portfolio`, `raw`, `alternative`, `chosen`, `descartes` |
| `--personajes` | string | `""` | Personajes separados por coma. Ej: `"brenda,maya"` |
| `--tags` | string | `""` | Tags libres separados por coma. Ej: `"colorido,playero,noche"` |
| `--location` | string | `""` | Ubicación general de la sesión. Ej: `"La Plata, AR"` |
| `--year` | int | del EXIF o sesión | Año de la sesión (override si no hay EXIF) |
| `--rating` | int | `0` | Rating 1-5 (pre-asignado, editable después) |
| `--selected` | flag | off | Marcar todas las fotos como selección editorial |
| `--description` | string | `""` | Descripción general de la sesión (texto libre) |

#### Comportamiento flags

| Flag | Tipo | Default | Descripción |
|------|------|---------|-------------|
| `--db` | string | global | ChromaDB path override |
| `--collection` | string | `"photos"` | Nombre de colección |
| `--model` | string | `siglip-so400m` | Modelo de embeddings |
| `--device` | string | `auto` | `auto` / `cuda` / `cpu` |
| `--recursive`, `-r` | flag | off | Escanear subdirectorios |
| `--include` | string | `*.jpg,*.jpeg,*.png` | Glob de inclusión (separado por comas) |
| `--exclude` | string | `""` | Glob de exclusión. Ej: `*_thumb.jpg,*_small.jpg` |
| `--dry-run` | flag | off | Solo mostrar qué se indexaría sin escribir |
| `--overwrite` | flag | off | Re-indexar aunque ya exista en ChromaDB |
| `--reset` | flag | off | Eliminar colección completa y salir |
| `--exif` / `--no-exif` | flag | `on` | Extraer EXIF automático (cámara, lente, ISO, etc.) |
| `--metadata` | string | `""` | JSON extra para metadata custom. Ej: `'{"cliente":"marina","tema":"boudoir"}'` |

#### Metadata auto-detectada (por foto, no requiere flags)

| Campo | Origen | Valores ejemplo |
|-------|--------|-----------------|
| `variante` | Parseo de filename | `original`, `v2`, `pop`, `moody_pop`, `vNEW` |
| `orientacion` | Dimensiones de imagen | `horizontal`, `vertical`, `cuadrada` |
| `color` | Análisis de canales RGB | `color`, `bw` |
| `fecha` | EXIF `DateTimeOriginal` o mtime | `2025-03-08` |
| `camara` | EXIF `Model` / `Make` | `ILCE-7M4`, `Canon EOS R5` |
| `lente` | EXIF `LensModel` | `FE 24-70mm F2.8 GM` |
| `focal` | EXIF `FocalLength` | `50.0` |
| `iso` | EXIF `ISOSpeedRatings` | `100` |
| `apertura` | EXIF `FNumber` | `2.8` |
| `filename` | — | `IMG_1234.jpg` |
| `path` | — | `/media/.../IMG_1234.jpg` |
| `format` | Extensión | `jpg`, `png` |

#### Ejemplos

```bash
# Mínimo
photor index ./fotos --session "brenda-pileta-kinky"

# Completo
photor index /media/dargonar/bkp_1t_new/portfolio/brenda_oleo-al-agua \
  --session "brenda-pileta-kinky" \
  --project "brenda" \
  --set "portfolio" \
  --personajes "brenda,maya" \
  --location "La Plata" \
  --year 2025 \
  --rating 4 \
  --tags "pileta,agua,verano" \
  --description "Sesión de Brenda y Maya en la pileta" \
  --recursive

# Solo preview
photor index ./raw --session "mila-beach" --dry-run

# Forzar CPU (cuando Pixtral está ocupando VRAM)
photor index ./fotos --session "at-home" --device cpu

# Reset + re-index
photor index --reset
photor index ./fotos --session "nueva-sesion"
```

---

### 3.2 `photor search`

Search indexed photos by semantic concept, optionally filtered by session.

```
photor search <query> [options]
```

**Arguments:**
- `query` — text query (positional)

**Options:**
- `--session`, `-s` — filter by session name
- `-n` — number of results (default: 10)
- `--db` — ChromaDB path
- `--model` — embedding model

**Special modes:**
```
photor search --sessions       # list all indexed sessions
photor search --stats          # show DB stats (total photos, per session)
```

**Output:**
- Ranked list with filename, similarity score (0-100%), session, absolute path
- Appends `MEDIA:/path` lines for easy integration with Hermes WebUI

---

### 3.3 `photor map`

Generate a visual concept map HTML. Runs multiple semantic queries against ChromaDB and produces an HTML file showing which photos match which concepts, plus a "nodal analysis" heatmap.

```
photor map <query_spec> [options]
```

**Argument (query_spec):** One of:
- A JSON file with an array of `{emoji, titulo, query}` objects
- Inline list: `"tensión, aislamiento, intimidad"`

**Options:**
- `--session`, `-s` — filter by session
- `-n` — results per concept (default: 15)
- `--title` — HTML page title
- `--output`, `-o` — output HTML path (default: auto-incremental)
- `--db`, `--model` — ChromaDB config

**Output:**
Self-contained HTML with:
- Concept→photo mapping (which photos match each concept)
- Nodal analysis (which photos match the most concepts)
- MEDIA: paths for inline images
- Color-coded scores per photo-concept pair

---

### 3.4 `photor raw2jpg`

Convert RAW files (ARW, CR2, NEF, DNG) to JPEG using rawpy.

```
photor raw2jpg <src> <dst> [options]
```

**Arguments:**
- `src` — source directory or file
- `dst` — destination directory

**Options:**
- `--quality` — JPEG quality (default: 95)
- `--max-size` — max dimension (default: 0 = no resize)
- `--camera-wb` — use camera white balance (default: True)
- `--half-size` — half resolution output (default: False)
- `--recursive`, `-r` — scan subdirectories
- `--dry-run` — preview only
- `--skip-existing` — skip if dest exists (default: True)

**Behavior:**
- Uses rawpy (libraw bindings) for conversion
- Embeds EXIF data in output JPEG
- Preserves directory structure when recursive

---

### 3.5 `photor crop`

Crop white/empty bands from Instagram-style photos (added by Instagram when converting to square), resize to max dimensions, and compress.

```
photor crop <src_dirs...> --dest <output_dir> [options]
```

**Arguments:**
- `src_dirs` — one or more source directories (positional, variadic)
- `--dest`, `-d` — output directory (required)

**Options:**
- `--threshold` — white pixel threshold 0-255 (default: 240)
- `--purity` — fraction of white pixels per row/col to consider a band (default: 0.95)
- `--max-size` — max dimension after resize (default: 1920)
- `--max-bytes` — max file size (default: 2MB)
- `--dry-run` — preview only

**Output:**
JPEG files with:
1. White bands removed (top/bottom/left/right)
2. Resized to fit max-size (maintaining aspect ratio)
3. Compressed with binary search on quality to fit max-bytes

---

### 3.6 `photor resize`

Recursively copy photos from source to destination, resizing and compressing.

```
photor resize <src> <dst> [options]
```

**Arguments:**
- `src` — source directory
- `dst` — destination directory

**Options:**
- `--quality` — initial JPEG quality (default: 95)
- `--max-size` — max dimension (default: 1920)
- `--max-bytes` — max file size (default: 2MB)
- `--flat` — copy flat (no subdirectory structure)
- `--dry-run` — preview only

**Behavior:**
- Recursively walks source, preserving relative directory structure
- Resizes to fit max-size (maintains aspect ratio, LANCZOS)
- Binary search on quality to meet max-bytes
- Always outputs JPEG (converts PNG, WebP, etc.)

---

## 4. Output conventions

### Common flags across all commands
- `--dry-run` — preview without writing/mutating anything
- `--quiet`, `-q` — minimal output
- `--verbose`, `-v` — detailed output
- `--help` — command help (built-in via click/typer)

### Exit codes
- `0` — success
- `1` — error (invalid args, missing input, processing failure)

### Media paths
- All absolute paths use `MEDIA:/path` format for Hermes WebUI inline display
- Output paths in maps use the same format

---

## 5. Directory structure

```
/media/dargonar/bkp_1t_new/portfolio/wdir/photor/
├── photor/                    # Python package
│   ├── __init__.py
│   ├── __main__.py            # python3 -m photor
│   ├── cli.py                 # click/typer entry point
│   ├── chroma.py              # ChromaDB client + helpers
│   ├── siglip.py              # SigLIP model wrapper (lazy load)
│   ├── raw_convert.py         # rawpy conversion
│   ├── crop.py                # white band cropping
│   ├── resize.py              # resize + compress
│   ├── map_generator.py       # concept map HTML generation
│   ├── map_template.html      # HTML template for maps
│   └── utils.py               # shared utilities (paths, formats, etc.)
├── pyproject.toml             # project config
├── requirements.txt           # dependencies
└── README.md                  # installation + usage
```

---

## 6. Implementation plan

| Phase | Commands | Depends on |
|-------|----------|-----------|
| **1** | `photor index`, `photor search`, `photor sessions`, `photor --stats` | (from existing photo_index.py + photo_search.py) |
| **2** | `photor raw2jpg` | rawpy + Pillow |
| **3** | `photor crop` | (from existing crop_white_bands.py) |
| **4** | `photor resize` | (from existing resize-photos.py) |
| **5** | `photor map` | (from existing mapeo.py + generar_html.py) |

---

## 7. Decisiones tomadas

| # | Pregunta | Decisión |
|---|----------|----------|
| 1 | Instalación | `python3 -m photor` (no pip) |
| 2 | Model caching | Sin cache. Carga en cada invocación. `--gpu`/`--cpu` para control explícito. |
| 3 | Template map | Usar el de `mapeo.py`. Parámetros vía JSON rediseñado. |
| 4 | Config file | `photor.yaml` en `photor/` para defaults. |
| 5 | EXIF en raw2jpg | ✅ Sí, extraer metadata EXIF de cada RAW y exportarla a JSON. |

---

## 8. Expansión de parámetros

### 8.1 `photor raw2jpg` — parametrización detallada

#### rawpy.postprocess params

| Flag | rawpy param | Default | Descripción |
|------|-------------|---------|-------------|
| `--camera-wb` / `--no-camera-wb` | `use_camera_wb` | `True` | Usar WB de la cámara |
| `--auto-bright` / `--no-auto-bright` | `no_auto_bright` | `False` (auto) | Corrección automática de brillo |
| `--bright` | `bright` | `1.0` | Factor de brillo (no apply si auto-bright) |
| `--half-size` | `half_size` | `False` | Salida a media resolución |
| `--output-bps` | `output_bps` | `8` | Bits por canal (8 o 16) |
| `--user-wb` | `user_wb` | `None` | WB manual `[r, g, b, g2]` |
| `--user-flip` | `user_flip` (rawpy) | `0` | Rotación manual (0=no, 3=180, 5=90CW, 6=90CCW) |
| `--gamma` | `gamma` | `(2.222, 4.5)` | Tupla gamma (aplica si no auto-bright) |
| `--highlight` | `highlight_mode` | `0` | Modo highlights (0=clip, 1=blend, 2=reconstruct) |
| `--exposure` | `exposure` | `1.0` | Ajuste de exposición (multiplicador) |
| `--fbdd` | `fbdd_noiserd` | `0` | Denoise (0=off, 1=light, 2=full) |
| `--median` | `med_passes` | `0` | Pasadas de filtro median para hot pixels |
| `--auto-wb` / `--no-auto-wb` | `use_auto_wb` | `False` | Auto white balance (vs camera) |

#### Output params

| Flag | Default | Descripción |
|------|---------|-------------|
| `--quality` | `95` | JPEG quality 1-100 |
| `--max-size` | `0` | 0 = full res. >0 = resize a max dimension |
| `--max-bytes` | `0` | 0 = sin límite. >0 = comprimir hasta ese peso |
| `--format` | `jpg` | Formato salida (jpg, png, tiff) |
| `--suffix` | `""` | Sufijo al filename (ej: `_edit`) |
| `--prefix` | `""` | Prefijo al filename |

#### EXIF output

Cuando `--exif-dir` está seteado, por cada RAW procesado se genera un archivo JSON con:

```json
{
  "filename": "IMG_1234.ARW",
  "output": "IMG_1234.jpg",
  "exif": {
    "make": "SONY",
    "model": "ILCE-7M4",
    "iso": 100,
    "aperture_f": 2.8,
    "shutter_speed": "1/125",
    "focal_mm": 50,
    "flash": false,
    "date": "2025-03-08T14:30:00",
    "lens": "FE 24-70mm F2.8 GM",
    "width": 9504,
    "height": 6336
  },
  "session": "andi-2",
  "path": "/media/.../IMG_1234.jpg"
}
```

| Flag | Default | Descripción |
|------|---------|-------------|
| `--exif-dir` | `None` | Directorio donde guardar los JSONs de EXIF (por foto) |
| `--exif-merged` | `None` | Path a un JSON único con todos los EXIFs mergeados |

#### Dry-run

| Flag | Default | Descripción |
|------|---------|-------------|
| `--dry-run` | `False` | Muestra qué RAW se convertirían, con metadatos extraídos sin escribir JPG |
| `--skip-existing` | `True` | Saltea si el JPG destino ya existe |

### 8.2 `photor crop` — parametrización detallada

#### White band detection

| Flag | Default | Rango | Descripción |
|------|---------|-------|-------------|
| `--threshold` | `240` | `0-255` | Valor mínimo RGB para considerar un pixel "blanco" |
| `--purity` | `0.95` | `0.0-1.0` | Fracción de píxeles blancos para considerar una fila/columna como banda |
| `--sides` | `all` | `all, top, bottom, left, right` | Qué lados recortar (útil para bandas asimétricas) |
| `--tolerance` | `0` | `0-50` | Píxeles extra a recortar después de detectar la banda (más agresivo) |

#### Resize

| Flag | Default | Descripción |
|------|---------|-------------|
| `--max-size` | `1920` | Dimensión máxima (mantiene aspect ratio). 0 = no resize |
| `--fit` | `inside` | `inside` (cabe dentro del box) o `cover` (llena el box, recorta) |
| `--no-resize` | `False` | Skip resize step entirely |

#### Compression

| Flag | Default | Descripción |
|------|---------|-------------|
| `--quality` | `95` | Quality JPEG inicial (binary search desde acá hacia abajo) |
| `--max-bytes` | `2097152` | Peso máximo en bytes (2 MB default) |
| `--no-compress` | `False` | Skip compression step (solo crop + resize) |

#### Output format

| Flag | Default | Descripción |
|------|---------|-------------|
| `--format` | `jpg` | Formato de salida (jpg, png, webp) |
| `--suffix` | `_cropped` | Sufijo al filename base |
| `--dest`, `-d` | _(required)_ | Directorio de salida |

#### Mode

| Flag | Default | Descripción |
|------|---------|-------------|
| `--dry-run` | `False` | Muestra qué detectaría sin escribir nada |
| `--visualize` | `False` | Genera una copia con las bandas detectadas marcadas en rojo (debug) |
| `--flat` | `False` | Copia plana (sin subdirectorios). Default: preserva estructura |

### 8.3 `photor resize` — parametrización detallada

#### Resize

| Flag | Default | Descripción |
|------|---------|-------------|
| `--max-size` | `1920` | Dimensión máxima (w o h). 0 = no resize |
| `--fit` | `inside` | `inside` (cabe en box) o `cover` (llena, recorta) |
| `--exact` | `None` | Resize exacto: `--exact 800x600` (deforma) |
| `--no-enlarge` | `False` | No agrandar imágenes más chicas que max-size |

#### Compression

| Flag | Default | Descripción |
|------|---------|-------------|
| `--quality` | `95` | Quality JPEG inicial |
| `--max-bytes` | `2097152` | 2 MB default. 0 = sin límite de peso |
| `--method` | `binary` | `binary` (binary search, óptimo) o `step` (step-down 5 en 5, más rápido) |
| `--min-quality` | `5` | Quality mínima antes de empezar a downscalar |

#### Downscale fallback

| Flag | Default | Descripción |
|------|---------|-------------|
| `--allow-downscale` | `True` | Si True, como último recurso reduce dimensiones |
| `--downscale-factor` | `0.1` | Paso de reducción (0.1 = 10% cada paso) |
| `--downscale-min` | `0.3` | Factor mínimo de escala (30% del original) |

#### Input/Output

| Flag | Default | Descripción |
|------|---------|-------------|
| `--convert-all` | `True` | Convertir a JPG incluso PNG/TIFF/BMP |
| `--format` | `jpg` | Formato salida |
| `--flat` | `False` | Copia plana (sin estructura de directorios) |
| `--keep-ext` | `False` | Mantener extensión original (no convertir a .jpg) |
| `--suffix` | `""` | Sufijo: `--suffix _web` → `foto_web.jpg` |

#### Dry-run

| Flag | Default | Descripción |
|------|---------|-------------|
| `--dry-run` | `False` | Muestra qué se procesaría |
| `--stats-only` | `False` | Solo contar archivos, sin procesar |

### 8.4 `photor map` — parametrización detallada

#### Query spec (JSON file)

Formato del archivo JSON de queries:

```json
[
  {
    "emoji": "🌊",
    "titulo": "Agua",
    "query": "agua, pileta, entorno acuático, swimming pool"
  },
  {
    "emoji": "💧",
    "titulo": "Reflejos",
    "query": "reflejos, destellos, brillos en el agua, light reflections"
  },
  {
    "emoji": "🤚",
    "titulo": "Piel",
    "query": "piel, tacto, desnudez, cuerpo, flesh, touch"
  }
]
```

| Campo | Requerido | Descripción |
|-------|-----------|-------------|
| `emoji` | ✅ | Emoji identificador del concepto |
| `titulo` | ✅ | Título visible en el HTML |
| `query` | ✅ | Texto de búsqueda (pueden ser múltiples términos separados por coma) |
| `query_en` | ❌ | Query en inglés (opcional, mezcla resultados si se provee) |

#### Search params

| Flag | Default | Descripción |
|------|---------|-------------|
| `-n` | `15` | Resultados por concepto |
| `--session`, `-s` | `None` | Filtrar por sesión |
| `--min-score` | `0.01` | Score mínimo (0-1) para incluir una foto |
| `--score-type` | `cosine` | `cosine` (similaridad) o `rank` (posición en ranking) |

#### Output

| Flag | Default | Descripción |
|------|---------|-------------|
| `--output`, `-o` | `None` | Path específico. Si no se da: auto-incremental (`mapeo_001.html`) |
| `--output-dir` | `None` | Directorio para auto-incremental (default: CWD) |
| `--title` | `"Mapa conceptual"` | Título de la página HTML |
| `--open` | `False` | Abrir el HTML en browser después de generar |
| `--exclude-below` | `0` | Excluir fotos que aparecen en menos de N conceptos (nodal filter) |

#### Path override

| Flag | Default | Descripción |
|------|---------|-------------|
| `--path-map` | `None` | JSON con reemplazos de path: `{"/old/":"/new/"}` |

#### Nodal analysis

| Flag | Default | Descripción |
|------|---------|-------------|
| `--nodal` | `True` | Incluir sección de análisis nodal (fotos que matchean más conceptos) |
| `--nodal-top` | `10` | Cuántas fotos mostrar en nodal |
| `--cluster` | `True` | Agrupar fotos por cluster de conceptos (co-occurrence) |

#### Theme

| Flag | Default | Descripción |
|------|---------|-------------|
| `--dark` | `True` | Tema oscuro |
| `--inline` | `True` | Inline MEDIA paths (si False, solo nombres de archivo) |

---

## 9. `photor.yaml` — estructura del config file

```yaml
# photor.yaml — defaults globales
chroma:
  path: /media/dargonar/bkp_1t_new/photo_index
  collection: photos

model:
  name: google/siglip-so400m-patch14-384
  device: auto          # auto | cuda | cpu

search:
  n_results: 10

raw2jpg:
  quality: 95
  camera_wb: true
  half_size: false
  output_bps: 8
  skip_existing: true
  format: jpg

crop:
  threshold: 240
  purity: 0.95
  max_size: 1920
  max_bytes: 2097152
  format: jpg

resize:
  max_size: 1920
  quality: 95
  max_bytes: 2097152
  method: binary
  format: jpg

map:
  n_results: 15
  dark: true
  inline: true
  output_dir: /media/dargonar/bkp_1t_new/portfolio/wdir
```

---

## 10. Source mapping

| Existing file | → New module | Notes |
|---------------|-------------|-------|
| `~/.hermes/scripts/photo_index.py` | `photor/cli.py` (index subcommand) | Simplify: remove --project/--set/--personajes |
| `~/.hermes/scripts/photo_search.py` | `photor/cli.py` (search) + `chroma.py` | Same interface |
| `~/workspace/mapeo/mapeo.py` | `photor/map_generator.py` | Reuse HTML template + query logic |
| `~/workspace/mapeo_brenda/generar_html.py` | `photor/map_generator.py` | Similar; merge into one |
| `wdir/crop_white_bands.py` | `photor/crop.py` | Direct migration |
| `wdir/resize-photos.py` | `photor/resize.py` | Direct migration |
| _(photo-batch-processing skill)_ | `photor/raw_convert.py` | Use rawpy approach from skill |
| `wdir/arw-to-jpg_*.sh` | _(obsoleted by raw2jpg)_ | ─ |
| `wdir/cr2-to-jpg_*.sh` | _(obsoleted by raw2jpg)_ | ─ |
| `wdir/indexer.sh` | _(obsoleted by `photor index`)_ | ─ |
| `wdir/mapeo.sh` | _(obsoleted by `photor map`)_ | ─ |
