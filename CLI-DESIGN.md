# 📷 `pf` — Portfolio CLI Tooling

## Inventario de scripts existentes

### 🔍 Búsqueda semántica (ChromaDB + SigLIP)

| Script | Ruta | Función |
|--------|------|---------|
| `photo_index.py` | `~/.hermes/scripts/photo_index.py` | Indexa fotos en ChromaDB con embeddings SigLIP |
| `photo_search.py` | `~/.hermes/scripts/photo_search.py` | Busca fotos por concepto/emoción, filtra por sesión |
| `mapeo.py` | `~/workspace/mapeo/mapeo.py` | Genera HTML con mapa conceptual: múltiples queries → heatmap visual |
| `generar_html.py` | `~/workspace/mapeo_brenda/generar_html.py` | Similar: busca 12 conceptos y genera HTML |

### 📸 Conversión RAW → JPG (bash + darktable-cli)

| Script | Sesión |
|--------|--------|
| `arw-to-jpg_andi_2.sh` | Andi sesión 2 |
| `arw-to-jpg_andi_raw.sh` | Andi raw |
| `arw-to-jpg_mila_only.sh` | Mila Only |
| `arw-to-jpg_mila_only_alternative.sh` | Mila Only (alt) |
| `arw-to-jpg_xxx.sh` | Sesión XXX |
| `cr2-to-jpg_brenda.sh` | Brenda |
| `cr2-to-jpg_brenda_variantes.sh` | Brenda variantes |
| `cr2-to-jpg_juli-fontan_faltantes.sh` | Juli Fontán (faltantes) |
| `cr2-to-jpg_mila_beach.sh` | Mila Beach |
| `cr2-to-jpg_mila_facu_recursivo.sh` | Mila Facu (recursivo) |
| `cr2-to-jpg_xxx.sh` | Sesión XXX |
| `cr2-to-jpg_xxx_recursivo.sh` | Sesión XXX (recursivo) |

→ **12 scripts casi idénticos**, varían solo INPUT_DIR, OUTPUT_DIR, EXCLUDE_DIRS

### 🖼️ Procesamiento de imágenes (Python)

| Script | Ruta | Función |
|--------|------|---------|
| `crop_white_bands.py` | `wdir/crop_white_bands.py` | Elimina bandas blancas de IG, redimensiona a 1920px, comprime a ≤2 MB |
| `resize-photos.py` | `wdir/resize-photos.py` | Redimensiona recursivo preservando estructura, comprime con binary search |
| `photo-batch-processing` | _(skill)_ | RAW→JPG (rawpy) + compresión con binary search + split |

### 🔧 Scripts auxiliares

| Script | Función |
|--------|---------|
| `indexer.sh` | Histórico de invocaciones a photo_index.py (hoy obsoleto) |
| `mapeo.sh` | Ejecuta mapeo.py |
| `sync.sh` | rsync portfolio → www/ |

---

## Propuesta: CLI `pf` (portfolio)

Un solo comando unificado en `/media/dargonar/bkp_1t_new/portfolio/wdir/`.

```bash
pf <comando> [args...]
```

### Subcomandos propuestos

| Comando | Función | Origen |
|---------|---------|--------|
| `pf index` | Indexar fotos → ChromaDB | `photo_index.py` |
| `pf search` | Buscar por concepto | `photo_search.py` |
| `pf map` | Generar mapa conceptual HTML | `mapeo.py` + `generar_html.py` |
| `pf raw2jpg` | Convertir ARW/CR2 → JPG | `arw-to-jpg_*.sh` unificados |
| `pf crop` | Sacar bandas blancas IG | `crop_white_bands.py` |
| `pf resize` | Redimensionar + copiar JPGs | `resize-photos.py` |
| `pf sessions` | Listar sesiones indexadas | `photo_search.py --list-sessions` |
| `pf stats` | Estadísticas de la DB | `photo_search.py --stats` |

### Detalle de cada subcomando

#### `pf index`
```bash
pf index --path /ruta/a/fotos --session "nombre-sesion"
# alias corto:
pf index /ruta/a/fotos -s "nombre-sesion"
```
Unifica los parámetros extra del indexer.sh original (--project, --set, --personajes) como metadata opcional.

#### `pf search`
```bash
pf search "tensión" -s brenda-maya-pileta-kinky
pf search "aislamiento" -n 20
pf search --sessions    # lista sesiones
pf search --stats       # estadísticas
```

#### `pf map`
```bash
pf map queries.json                    # desde archivo
pf map "tensión,aislamiento,intimidad" # desde inline
pf map -s brenda-maya-pileta-kinky     # filtrado por sesión
```
Genera un HTML interactivo con heatmap de qué fotos matchean qué conceptos.

#### `pf raw2jpg`
```bash
pf raw2jpg /ruta/raw --dest /ruta/jpg
pf raw2jpg /ruta/raw --dest /ruta/jpg --quality 95 --camera-wb
# recursivo subdirectorios:
pf raw2jpg /ruta/raw --dest /ruta/jpg --recursive
```
Reemplaza los 12 scripts ARW/CR2 casi idénticos con un solo comando parametrizable.

#### `pf crop`
```bash
pf crop /dir/de/fotos --dest /output
pf crop /dir1 /dir2 --dest /output --threshold 240 --dry-run
```
Saca bandas blancas de Instagram, redimensiona a 1920px, comprime a ≤2 MB.

#### `pf resize`
```bash
pf resize /origen /destino
pf resize /origen /destino --quality 90 --max-size 2560 --dry-run
```
Copia recursiva redimensionando + comprimiendo, preserva estructura de directorios.

---

### Estructura del CLI

```text
/media/dargonar/bkp_1t_new/portfolio/wdir/
├── pf                      ← entry point (bash wrapper)
├── lib/
│   ├── __init__.py
│   ├── chroma.py           ← lógica compartida ChromaDB
│   ├── images.py           ← procesamiento de imágenes (raw, crop, resize)
│   └── map_generator.py    ← generación de HTML
├── scripts/
│   ├── photo_index.py      ← (actual, movido acá)
│   ├── photo_search.py     ← (actual, movido acá)
│   └── ...
└── templates/
    └── map.html            ← template para mapas conceptuales
```

---

### Preguntas abiertas

1. **¿Nombre del CLI?** `pf` (portfolio-fotos) o preferís otro?
2. **¿Migrar scripts existentes** de `~/.hermes/scripts/` y `~/workspace/mapeo/` a `wdir/` o dejar symlinks?
3. **¿`pf raw2jpg` usa darktable-cli** (como los scripts actuales) o **rawpy** (como el skill photo-batch-processing)?
   - darktable-cli: más control de revelado, más lento
   - rawpy: más rápido, menos control
4. **¿Modo dry-run** en todos los comandos destructivos?
5. **¿Querés que el CLI sea bash wrapper + Python puro**, o preferís **click/typer** (framework Python para CLIs)?