/* ── photor map — App ──────────────────────────────────── */

let state = {
  queries: [],          // current query rows
  filters: {},          // active filters
  results: null,        // current results HTML + stats
  history: [],          // list of past queries
  activeHistoryId: null, // selected history item
  loading: false,
};

// ── DOM refs ──
const $ = (s) => document.querySelector(s);
const $$ = (s) => document.querySelectorAll(s);

const el = {
  runBtn: () => document.getElementById('btn-run'),
  filtersPanel: () => document.getElementById('filters-panel'),
  filtersForm: () => document.getElementById('filters-form'),
  results: () => document.getElementById('results'),
  resultsTitle: () => document.getElementById('results-title'),
  resultsStats: () => document.getElementById('results-stats'),
  resultsBody: () => document.getElementById('results-body'),
  loading: () => document.getElementById('loading'),
  empty: () => document.getElementById('empty-state'),
  error: () => document.getElementById('error-box'),
  history: () => document.getElementById('history-list'),
  newBtn: () => document.getElementById('btn-new'),
  searchInput: () => document.getElementById('search-input'),
  downloadBtn: () => document.getElementById('btn-download'),
  copyBtn: () => document.getElementById('btn-copy'),
  confirmOverlay: () => document.getElementById('confirm-overlay'),
  confirmMsg: () => document.getElementById('confirm-msg'),
  confirmYes: () => document.getElementById('confirm-yes'),
  confirmNo: () => document.getElementById('confirm-no'),
};

// ── Init ──
document.addEventListener('DOMContentLoaded', async () => {
  // Load sessions for filter dropdowns
  await loadFilterOptions();

  // Load history
  await loadHistory();

  // Event listeners
  el.runBtn().addEventListener('click', runQuery);
  el.newBtn().addEventListener('click', newQuery);
  const ft = document.getElementById('filters-toggle');
  if (ft) ft.addEventListener('click', toggleFilters);
  el.searchInput().addEventListener('input', filterResults);
  el.downloadBtn().addEventListener('click', downloadHTML);
  el.copyBtn().addEventListener('click', copyPath);
  el.confirmYes().addEventListener('click', confirmDelete);
  el.confirmNo().addEventListener('click', () => el.confirmOverlay().classList.remove('visible'));

  // Keyboard shortcut: Ctrl+Enter to run
  document.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      e.preventDefault();
      runQuery();
    }
  });
});

// ── Query parsing ──
function getQueryRows() {
  const text = document.getElementById('query-textarea').value;
  const rows = [];
  text.split('\n').forEach((line) => {
    line = line.trim();
    if (!line) return;
    // Format: "Title: query terms, more terms"
    const colonIdx = line.indexOf(':');
    if (colonIdx === -1) {
      // No colon: use the whole line as both title and query
      if (line) rows.push({ emoji: '📷', titulo: line, query: line });
      return;
    }
    const titulo = line.substring(0, colonIdx).trim();
    const query = line.substring(colonIdx + 1).trim();
    if (titulo && query) {
      rows.push({ emoji: '📷', titulo, query });
    } else if (query) {
      rows.push({ emoji: '📷', titulo: query, query });
    }
  });
  return rows;
}

function setQueryRows(queries) {
  const text = (queries || [])
    .map((q) => `${q.titulo}: ${q.query}`)
    .join('\n');
  document.getElementById('query-textarea').value = text;
}

// ── Filters ──
function toggleFilters() {
  el.filtersPanel().classList.toggle('open');
}

async function loadFilterOptions() {
  try {
    const [sessRes, projRes] = await Promise.all([
      fetch('/api/sessions'),
      fetch('/api/projects')
    ]);
    const sessData = await sessRes.json();
    const projData = await projRes.json();

    // Sessions datalist (autocomplete)
    const sessList = document.getElementById('session-list');
    sessData.sessions.forEach((s) => {
      const opt = document.createElement('option');
      opt.value = s.name;
      opt.textContent = `${s.name} (${s.count})`;
      sessList.appendChild(opt);
    });

    // Projects datalist (autocomplete)
    const projList = document.getElementById('project-list');
    projData.projects.forEach((p) => {
      const opt = document.createElement('option');
      opt.value = p.name;
      opt.textContent = `${p.name} (${p.count})`;
      projList.appendChild(opt);
    });
  } catch (e) {
    console.warn('Error loading filter options:', e);
  }
}

function getFilters() {
  const form = el.filtersForm();
  const data = {};
  new FormData(form).forEach((value, key) => {
    if (value) data[key] = value;
  });
  return data;
}

function setFilters(filters) {
  const form = el.filtersForm();
  Object.entries(filters || {}).forEach(([key, value]) => {
    const input = form.querySelector(`[name="${key}"]`);
    if (input) input.value = value || '';
  });
}

// ── API calls ──
async function runQuery() {
  const queries = getQueryRows();
  if (queries.length === 0) {
    showError('Agregá al menos una línea de búsqueda');
    return;
  }

  const filters = getFilters();
  const request = {
    queries,
    n_results: parseInt(filters.n_results || '15'),
    nodal_top: parseInt(filters.nodal_top || '10'),
    dark: true,
  };
  ['session', 'project', 'set', 'color', 'orientacion', 'personajes'].forEach((k) => {
    if (filters[k]) request[k] = filters[k];
  });

  setLoading(true);
  hideError();

  try {
    const res = await fetch('/api/map', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    });

    const data = await res.json();

    if (!res.ok) {
      showError(data.error || 'Error del servidor');
      if (data.stderr) console.error('STDERR:', data.stderr);
      setLoading(false);
      return;
    }

    // Show results
    showResults(data);
    // Refresh history
    await loadHistory();
    // Highlight this item
    state.activeHistoryId = data.id;
    highlightHistoryItem(data.id);
  } catch (e) {
    showError(`Error de conexión: ${e.message}`);
  }

  setLoading(false);
}

// ── Results display ──
function showResults(data) {
  state.results = data;
  el.empty().style.display = 'none';
  el.results().classList.add('visible');

  el.resultsTitle().textContent = data.title || 'Resultados';
  el.resultsStats().textContent = `${data.stats.unique_photos} fotos · ${data.stats.concepts} conceptos`;

  // Show link to HTML file
  const path = data.path || '';
  const fileName = path.split('/').pop();
  el.resultsBody().innerHTML = `
    <div class="result-link">
      <div class="result-link-icon">📊</div>
      <div class="result-link-info">
        <a href="file://${path}" target="_blank" class="result-link-file">
          ${escapeHtml(fileName)}
        </a>
        <div class="result-link-path">${escapeHtml(path)}</div>
      </div>
      <a href="/api/map-file?path=${encodeURIComponent(path)}&download=1" class="btn" download>💾</a>
    </div>
  `;

  // Store result path for copy action
  el.resultsBody().dataset.path = path;
}

function filterResults() {
  const q = el.searchInput().value.toLowerCase();
  // For now, simply pass the filter query to the iframe
  // (full implementation would filter the iframe's DOM)
}

function newQuery() {
  document.getElementById('query-textarea').value = '';
  setFilters({});
  el.results().classList.remove('visible');
  el.empty().style.display = 'block';
  state.activeHistoryId = null;
  highlightHistoryItem(null);
  el.searchInput().value = '';
  hideError();
}

// ── History ──
async function loadHistory() {
  try {
    const res = await fetch('/api/queries');
    const data = await res.json();
    state.history = data.queries || [];
    renderHistory();
  } catch (e) {
    console.warn('Error loading history:', e);
  }
}

function renderHistory() {
  const list = el.history();
  list.innerHTML = '';

  if (state.history.length === 0) {
    list.innerHTML = '<div style="padding:20px;text-align:center;color:var(--muted);font-size:12px;">Sin historial</div>';
    return;
  }

  state.history.forEach((q) => {
    const item = document.createElement('div');
    item.className = 'history-item';
    if (q.id === state.activeHistoryId) item.classList.add('active');
    item.dataset.id = q.id;

    item.innerHTML = `
      <div class="h-title">
        ${q.result_path
          ? `<a href="file://${q.result_path}" target="_blank" class="h-link" onclick="event.stopPropagation();">${escapeHtml(q.title)}</a>`
          : escapeHtml(q.title)}
      </div>
      <div class="h-meta">
        <span>${escapeHtml(q.time_ago)} · <span class="h-badge">${q.stats?.unique_photos || '?'} fotos</span></span>
        <span class="h-delete" title="Eliminar">🗑️</span>
      </div>
    `;

    // Click to restore
    item.addEventListener('click', (e) => {
      if (e.target.classList.contains('h-delete')) return;
      restoreQuery(q.id);
    });

    // Delete
    item.querySelector('.h-delete').addEventListener('click', (e) => {
      e.stopPropagation();
      promptDelete(q.id, q.title);
    });

    list.appendChild(item);
  });
}

function highlightHistoryItem(id) {
  el.history().querySelectorAll('.history-item').forEach((item) => {
    item.classList.toggle('active', item.dataset.id == id);
  });
}

async function restoreQuery(id) {
  try {
    const res = await fetch('/api/queries');
    const data = await res.json();
    const q = data.queries.find((x) => x.id === id);
    if (!q) return;

    state.activeHistoryId = id;
    highlightHistoryItem(id);

    // Restore query text into textarea
    const request = q.request || {};
    const queries = request.queries || [];
    if (queries.length > 0) {
      setQueryRows(queries);
    }

    // Restore filters
    const filters = {};
    ['session','project','set','color','orientacion','personajes'].forEach((k) => {
      if (request[k]) filters[k] = request[k];
    });
    if (request.n_results) filters.n_results = request.n_results;
    if (request.nodal_top) filters.nodal_top = request.nodal_top;
    setFilters(filters);

    // Load HTML result
    if (q.result_path) {
      try {
        const htmlRes = await fetch(`/api/map-file?path=${encodeURIComponent(q.result_path)}`);
        if (htmlRes.ok) {
          const htmlData = await htmlRes.json();
          showResults({
            id: q.id,
            title: q.title,
            stats: q.stats,
            path: q.result_path,
            created_at: q.created_at,
          });
          return;
        }
      } catch (e) {
        // fall through to re-run
      }
    }

    // If HTML couldn't be loaded, re-run the query
    runQuery();

  } catch (e) {
    console.warn('Error restoring query:', e);
  }
}

// ── Delete ──
let pendingDeleteId = null;

function promptDelete(id, title) {
  pendingDeleteId = id;
  el.confirmMsg().textContent = `¿Eliminar "${title}" del historial?`;
  el.confirmOverlay().classList.add('visible');
}

async function confirmDelete() {
  if (!pendingDeleteId) return;
  el.confirmOverlay().classList.remove('visible');

  try {
    const res = await fetch(`/api/queries/delete/${pendingDeleteId}`, { method: 'POST' });
    if (res.ok) {
      if (state.activeHistoryId === pendingDeleteId) {
        newQuery();
      }
      await loadHistory();
    }
  } catch (e) {
    console.warn('Error deleting query:', e);
  }
  pendingDeleteId = null;
}

// ── Actions ──
function downloadHTML() {
  const path = state.results?.path;
  if (!path) return;
  const a = document.createElement('a');
  a.href = `/api/map-file?path=${encodeURIComponent(path)}&download=1`;
  a.download = `mapeo_${state.results.id || 'resultado'}.html`;
  a.click();
}

function copyPath() {
  const path = state.results?.path;
  if (!path) return;
  navigator.clipboard.writeText(path).catch(() => {});
  el.copyBtn().textContent = '✅ Copiado';
  setTimeout(() => { el.copyBtn().textContent = '📋 Ruta'; }, 2000);
}

// ── UI helpers ──
function setLoading(v) {
  state.loading = v;
  el.runBtn().disabled = v;
  el.loading().classList.toggle('visible', v);
}

function showError(msg) {
  el.error().textContent = msg;
  el.error().classList.add('visible');
}

function hideError() {
  el.error().classList.remove('visible');
}

function escapeHtml(s) {
  if (!s) return '';
  const d = document.createElement('div');
  d.textContent = s;
  return d.innerHTML;
}