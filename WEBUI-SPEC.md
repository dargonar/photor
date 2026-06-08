# `photor map` — Web UI Spec v1

## Overview

Web UI para `photor map` que permite construir queries conceptuales visualmente, ejecutarlas contra ChromaDB, y ver los resultados como mapas conceptuales HTML interactivos. Todo corre con un solo comando: `python3 -m photor serve`.

---

## 1. Estética

Inspirada en [hermes-webui](https://github.com/nesquena/hermes-webui):

**Paleta (dark mode):**
| Variable | Color | Uso |
|----------|-------|-----|
| `--bg` | `#111` | Fondo general |
| `--sidebar` | `#1a1a1a` | Sidebar izquierdo |
| `--surface` | `#1e1e1e` | Tarjetas, inputs |
| `--border` | `#2a2a2a` | Bordes |
| `--text` | `#e0e0e0` | Texto principal |
| `--muted` | `#888` | Texto secundario |
| `--accent` | `#b8860b` | Acento dorado (links, botones) |
| `--accent-hover` | `#d4a017` | Hover de acento |
| `--error` | `#ef5350` | Errores |
| `--success` | `#66bb6a` | Éxito |

**Layout:** Sidebar 320px + contenido principal. Sin scroll en body, cada panel scrolla independientemente.

**Fuente:** `-apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif`

---

## 2. Layout

```
┌─────────────────────────────────────────────────────────┐
│ ┌──────────┐  ┌────────────────────────────────────────┐│
│ │ SIDEBAR  │  │ HEADER                                 ││
│ │          │  │  [🔍 Buscar fotos...             ]     ││
│ │ Historial│  │────────────────────────────────────────││
│ │ de       │  │ QUERY FORM                             ││
│ │ queries  │  │ ┌────────────────────────────────────┐ ││
│ │          │  │ │ 🌊 Agua     | agua, pileta, mar   │ ││
│ │ previas  │  │ │ 🤚 Piel     | piel, tacto, cuerpo │ ││
│ │          │  │ │ 💧 Reflejos | reflejos, destellos │ ││
│ │          │  │ │ [➕ Agregar fila] [▶ Ejecutar]    │ ││
│ │          │  │ └────────────────────────────────────┘ ││
│ │          │  │────────────────────────────────────────││
│ │          │  │ RESULTS (concept map HTML)              ││
│ │          │  │ ┌────────────────────────────────────┐ ││
│ │          │  │ │ Grid de fotos por concepto         │ ││
│ │          │  │ │ Nodal/bisagra analysis             │ ││
│ │          │  │ │ ...                                │ ││
│ │          │  │ └────────────────────────────────────┘ ││
│ └──────────┘  └────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────┘
```

---

## 3. Componentes

### 3.1 Sidebar (izquierda, 320px fijo)

- **Título:** "photor map" con logo
- **Nueva query:** Botón "✏️ Nueva" (limpia el formulario)
- **Historial:** Lista de queries ejecutadas, cada una con:
  - Título autogenerado: `"🌊 Agua, 🤚 Piel..."` (emoji + primeros títulos)
  - Fecha/hora de ejecución
  - Badge con cantidad de resultados (ej: "49 fotos")
  - Indicador de filtros activos (si aplica)
  - **Hover:** color de fondo cambiante
  - **Click:** restaura la query en el formulario Y muestra sus resultados
  - **Menú contextual:** opción "Eliminar" (con confirmación)

### 3.2 Header

- Título grande: **"📷 Mapa Conceptual"**
- **Barra de búsqueda rápida:** input tipo search que filtra las fotos en los resultados actuales (filtro local por nombre de archivo)

### 3.3 Query Form

Formulario de múltiples filas. **Cada fila** representa un concepto a buscar:

| Campo | Tipo | Default | Descripción |
|-------|------|---------|-------------|
| `emoji` | text corto 🌊 | `""` | Emoji identificador del concepto |
| `titulo` | text | `""` | Título visible en el mapa |
| `query` | textarea small | `""` | Términos de búsqueda separados por coma |

**Comportamiento:**
- Cada fila tiene un botón ❌ para eliminarla
- Botón **"➕ Agregar fila"** al final
- Botón **"▶ Ejecutar"** en la parte inferior del formulario

**Filtros avanzados** (collapsable, toggle "⚙️ Filtros"):

| Filtro | Tipo | Descripción |
|--------|------|-------------|
| `Sesión` | dropdown | Filtra por sesión (cargado de ChromaDB) |
| `Proyecto` | dropdown | Filtra por proyecto |
| `Set` | dropdown | portfolio, raw, default... |
| `Color` | dropdown (color/bw) | Filtra por color o B&N |
| `Orientación` | dropdown (h/v/c) | Filtra por orientación |
| `Personajes` | dropdown | Filtra por personajes |
| `Resultados por concepto` | number | Default: 15 |
| `Máx fotos nodales` | number | Default: 10 |

**Predefinidos:** Botones rápidos para cargar queries pre-hechas:
- "🎨 General" → carga `queries_ejemplo.json`
- "💧 Agua & Piel" → carga las queries de brenda
- "📣 Marchas" → carga queries + filtro `set: portfolio`

**Persistencia:** El estado del formulario se guarda en el historial (localStorage) cuando se ejecuta.

### 3.4 Results Area

Muestra el mapa conceptual generado inline (embebido como HTML). 

**Tabs en resultados:**
1. **📊 Mapa** — El concepto map HTML embebido
2. **📋 JSON** — Los datos crudos de resultados (para debug/export)
3. **🔗 Compartir** — Link al archivo HTML generado

**Barra de acciones:**
- 💾 Guardar HTML (descarga el archivo)
- 📋 Copiar ruta del HTML generado
- 🗑️ Limpiar resultados

---

## 4. Backend API

### Servidor: `python3 -m photor serve [--port 9000]`

### Endpoints

#### `GET /`
Sirve el `index.html` de la UI.

#### `GET /api/sessions`
Devuelve lista de sesiones disponibles. (Reusa `search --sessions`)

```json
{"sessions": [{"name": "brenda-pileta-kinky", "count": 49}, ...]}
```

#### `GET /api/projects`
Devuelve lista de proyectos. (Reusa `search --stats`)

```json
{"projects": [{"name": "brenda", "count": 1730}, ...]}
```

#### `POST /api/map`
Ejecuta una query conceptual. (Reusa `map_generator.generate_map()`)

**Request:**
```json
{
  "queries": [
    {"emoji": "🌊", "titulo": "Agua", "query": "agua, pileta, mar"},
    {"emoji": "🤚", "titulo": "Piel", "query": "piel, tacto, cuerpo"}
  ],
  "session": "brenda-pileta-kinky",
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
  "html": "<!DOCTYPE html>...",
  "path": "/media/.../mapeo_001.html",
  "stats": {
    "total_entries": 75,
    "unique_photos": 49,
    "concepts": 2
  }
}
```

#### `GET /api/history`
Devuelve el historial de queries desde localStorage (opcional: desde un archivo en disco).

---

## 5. Persistencia

| Dato | Dónde se guarda | Formato |
|------|-----------------|---------|
| Historial de queries | `localStorage` (browser) | `photor_map_history` |
| HTML generados | `wdir/photor/maps/` | `mapeo_NNN.html` |
| Preferencias de UI | `localStorage` | `photor_map_prefs` |

---

## 6. Estructura de archivos

```
/media/dargonar/bkp_1t_new/portfolio/wdir/photor/photor/
├── serve.py                  # Servidor HTTP (http.server + API routes)
├── server_static/
│   ├── index.html            # Single-page app
│   ├── style.css             # Estilos (tema oscuro, layout)
│   └── app.js                # Lógica frontend (SPA, fetch API, localStorage)
├── map_generator.py          # (existente) lógica de generación de mapas
├── chroma.py                 # (existente) ChromaDB wrapper
├── siglip.py                 # (existente) modelo SigLIP
└── ...
```

---

## 7. Flujo de uso

```text
1. Usuario ejecuta: python3 -m photor serve
2. Se abre browser en http://localhost:9000
3. Usuario ve sidebar vacío + formulario vacío
4. Usuario completa filas del formulario (emoji, título, query)
     o hace click en un predefinido ("🎨 General")
5. Opcional: expande "⚙️ Filtros" y selecciona sesión/proyecto/etc.
6. Click "▶ Ejecutar"
7. Backend recibe POST /api/map, ejecuta generate_map()
8. Frontend recibe HTML + stats, renderiza en results area
9. La query se agrega al historial en sidebar
10. Usuario puede hacer click en cualquier item del historial para restaurarlo
```

---

## 8. Consideraciones técnicas

- **Sin dependencias externas**: solo `http.server` de stdlib
- **API asíncrona**: las queries pueden demorar ~30-60 seg (SigLIP en CPU). El frontend muestra un spinner/barra de progreso.
- **El modelo SigLIP se carga una vez** al iniciar el servidor y se reusa en todas las queries.
- **Historial efímero en localStorage**: si se borra el cache del browser, se pierde. Opcional: guardar en disco.
- **Los HTML generados** se guardan en `wdir/photor/maps/` con nombre incremental.
- **Responsive**: el sidebar se oculta en mobile (<768px), aparece con hamburger menu.

---

## 9. Próximos pasos (después de este spec)

1. Crear `serve.py` (servidor HTTP con rutas API)
2. Crear `server_static/index.html` (SPA)
3. Crear `server_static/style.css` (tema oscuro tipo hermes-webui)
4. Crear `server_static/app.js` (lógica frontend)
5. Probar end-to-end
6. Agregar a los comandos del CLI (`photor --help` debe mostrar `serve`)
