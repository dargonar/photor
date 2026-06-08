# `photor map` — Web UI Spec v2

## Overview

Web UI para `photor map` que permite construir queries conceptuales, ejecutarlas, ver resultados como mapas conceptuales HTML, y mantener un historial persistente en SQLite.

**Comando:** `python3 -m photor serve [--port 9000]`

---

## 1. Arquitectura: SigLIP solo en CLI, nunca en el server

**Problema original:** Cada comando CLI (`search`, `map`, `index`) cargaba SigLIP desde cero, incluso en procesos separados. El server cargaba SigLIP en memoria para cada request.

**Solución:**
- `photor index` → carga SigLIP **una vez** al inicio y reusa para todas las fotos (ya resuelto)
- `photor search` → necesita SigLIP para codificar el texto de búsqueda (arquitectura actual)
- `photor map` (CLI) → carga SigLIP, genera el HTML, termina
- `photor serve` (Web UI) → **NUNCA carga SigLIP**. Delega la generación de mapas al CLI como subproceso:

```text
POST /api/map
  → servidor escribe queries a archivo temporal
  → servidor spawn: python3 -m photor map /tmp/queries.json -o /output/mapeo_NNN.html
  → servidor espera resultado (timeout 300s)
  → servidor devuelve HTML al frontend
```

---

## 2. Base de datos: SQLite

**Archivo:** `wdir/photor/photor.db`

### Tabla: `queries`

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `id` | INTEGER PK AUTOINCREMENT | ID único |
| `created_at` | TEXT (ISO 8601) | Fecha/hora de ejecución |
| `title` | TEXT | Título autogenerado (primeros emojis + títulos) |
| `request_json` | TEXT (JSON) | Request completo enviado a POST /api/map |
| `result_path` | TEXT | Ruta al archivo HTML generado |
| `stats_json` | TEXT (JSON) | Estadísticas del resultado (total_entries, unique_photos, concepts) |
| `session` | TEXT | Filtro de sesión usado (si aplica) |
| `project` | TEXT | Filtro de proyecto usado (si aplica) |

---

## 3. API endpoints

### `GET /`

Sirve el `index.html` de la SPA.

### `GET /api/sessions`

Lista sesiones disponibles. Reusa `chroma.list_sessions()`.

```json
{"sessions": [{"name": "brenda-pileta-kinky", "count": 49}, ...]}
```

### `GET /api/queries`

Lista todas las queries guardadas en SQLite, ordenadas por fecha descendente.

```json
{
  "queries": [
    {
      "id": 1,
      "created_at": "2026-06-05T15:30:00",
      "title": "🌊 Agua, 🤚 Piel, 💧 Reflejos",
      "result_path": "/media/.../mapeo_001.html",
      "stats": {"total_entries": 60, "unique_photos": 49, "concepts": 3},
      "session": "brenda-pileta-kinky",
      "project": "brenda"
    }
  ]
}
```

### `POST /api/map`

Ejecuta una query conceptual. Guarda el request en SQLite con timestamp.

**Request:**
```json
{
  "queries": [
    {"emoji": "🌊", "titulo": "Agua", "query": "agua, pileta, mar"},
    {"emoji": "🤚", "titulo": "Piel", "query": "piel, tacto, cuerpo"}
  ],
  "session": "",
  "project": "",
  "set": "",
  "color": "",
  "orientacion": "",
  "personajes": "",
  "n_results": 15,
  "nodal_top": 10,
  "dark": true
}
```

**Response:**
```json
{
  "id": 1,
  "html": "<!DOCTYPE html>...",
  "path": "/media/.../mapeo_001.html",
  "stats": {
    "total_entries": 60,
    "unique_photos": 49,
    "concepts": 2
  },
  "created_at": "2026-06-05T15:30:00"
}
```

### `POST /api/queries/delete/<query_id>`

Elimina una query de SQLite. El archivo HTML se conserva en disco.

```json
{"status": "deleted", "id": 1}
```

---

## 4. Layout

```
┌─── 320px ────────────────────┬──────────────────────────────────┐
│  SIDEBAR                     │  HEADER                          │
│  📷 photor map               │  🔍 [Buscar en resultados...]    │
│  ─────────────────────       │──────────────────────────────────│
│  ✏️ Nueva                    │  QUERY FORM                      │
│                               │  ┌─────────────────────────────┐│
│  Historial:                   │  │ 🌊 | Agua | agua, pileta    ││
│  ┌─────────────────────────┐  │  │ 🤚 | Piel  | piel, tacto   ││
│  │ 🌊 Agua, 🤚 Piel,...   │  │  │ [➕] [⚙️ Filtros] [▶ Ejec.]││
│  │ hace 5 min · 49 fotos   │  │  └─────────────────────────────┘│
│  │ 🗑️                       │  │──────────────────────────────────│
│  ├─────────────────────────┤  │  RESULTS (concept map HTML)      │
│  │ 📣 Marchas, 🔥 Kinky... │  │  ┌─────────────────────────────┐│
│  │ hace 2h · 120 fotos     │  │  │ Grid de fotos por concepto ││
│  │ 🗑️                       │  │  │ Nodal/bisagra analysis     ││
│  └─────────────────────────┘  │  │ Estadísticas: N fotos, M... ││
│                               │  └─────────────────────────────┘│
└───────────────────────────────┴──────────────────────────────────┘
```

---

## 5. Query Form

| Componente | Descripción |
|------------|-------------|
| Filas de query | Cada fila: emoji (text) + título (text) + query (text). Botón ❌ para eliminar |
| ➕ Agregar fila | Agrega una fila vacía al final |
| ⚙️ Filtros | Panel colapsable con: Sesión (dropdown), Proyecto (dropdown), Set (dropdown), Color (dropdown), Orientación (dropdown), Personajes (dropdown), N resultados (number, default 15), Nodal top (number, default 10) |
| ▶ Ejecutar | Ejecuta la query (el botón se deshabilita durante la ejecución, muestra spinner) |

**No hay botones predefinidos.**

---

## 6. Sidebar

- **Título fijo:** "📷 photor map"
- **Botón "✏️ Nueva":** limpia el formulario y los resultados
- **Historial:** lista de queries desde SQLite, orden descendente por fecha
  - Cada item: título autogenerado (primeros emojis + títulos), timestamp relativo, badge de fotos
  - **Click:** restaura la query en el formulario y carga sus resultados
  - **🗑️** botón de eliminar (pide confirmación)
  - Item activo resaltado

---

## 7. Persistencia

| Dato | Dónde | Formato |
|------|-------|---------|
| Historial de queries | SQLite | `wdir/photor/photor.db` |
| HTML generados | Disco | `wdir/photor/maps/mapeo_NNN.html` |

---

## 8. Estructura de archivos

```
/media/dargonar/bkp_1t_new/portfolio/wdir/photor/photor/
├── serve.py                  # Servidor HTTP + SQLite + API
├── server_static/
│   ├── index.html            # Single-page app
│   ├── style.css             # Estilos tema oscuro
│   └── app.js                # Lógica frontend
├── map_generator.py          # (existente) CLI map generation
├── chroma.py                 # (existente) ChromaDB wrapper
└── ...
```

---

## 9. Nota sobre SigLIP

- **`photor index`**: carga SigLIP una vez al inicio, reusa para todas las fotos (optimizado)
- **`photor search`**: necesita SigLIP para codificar texto de búsqueda (por diseño)
- **`photor map` (CLI)**: necesita SigLIP para codificar queries textuales (por diseño)
- **`photor serve` (Web UI)**: **NUNCA** carga SigLIP. Delega al CLI como subproceso.