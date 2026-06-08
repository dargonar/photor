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
  queryRows: () => document.getElementById('query-rows'),
  addRowBtn: () => document.getElementById('btn-add-row'),
  runBtn: () => document.getElementById('btn-run'),
  filtersToggle: () => document.getElementById('filters-toggle'),
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
  // Add initial 2 query rows
  addQueryRow();
  addQueryRow();

  // Load sessions for filter dropdowns
  await loadFilterOptions();

  // Load history
  await loadHistory();

  // Event listeners
  el.addRowBtn().addEventListener('click', () => addQueryRow());
  el.runBtn().addEventListener('click', runQuery);
  el.filtersToggle().addEventListener('click', toggleFilters);
  el.newBtn().addEventListener('click', newQuery);
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

// ── Query rows ──
function addQueryRow(emoji = '', titulo = '', query = '') {
  const row = document.createElement('div');
  row.className = 'query-row';
  row.innerHTML = `
    <input class="qr-emoji" placeholder="🌊" value="${escapeHtml(emoji)}" maxlength="4">
    <input class="qr-title" placeholder="Título" value="${escapeHtml(titulo)}">
    <input class="qr-query" placeholder="agua, pileta, mar..." value="${escapeHtml(query)}">
    <button class="qr-remove" title="Eliminar fila">✕</button>
  `;
  row.querySelector('.qr-remove').addEventListener('click', () => {
    if (document.querySelectorAll('.query-row').length > 1) {
      row.remove();
    }
  });
  // Also support Enter to add new row
  row.querySelector('.qr-query').addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      addQueryRow();
      // Focus the new row's emoji
      const rows = document.querySelectorAll('.query-row');
      rows[rows.length - 1].querySelector('.qr-emoji').focus();
    }
  });
  el.queryRows().appendChild(row);
}

function getQueryRows() {
  const rows = [];
  document.querySelectorAll('.query-row').forEach((row) => {
    const emoji = row.querySelector('.qr-emoji').value.trim();
    const titulo = row.querySelector('.qr-title').value.trim();
    const query = row.querySelector('.qr-query').value.trim();
    if (query) {
      rows.push({ emoji: emoji || '📷', titulo: titulo || query.split(',')[0].trim(), query });
    }
  });
  return rows;
}

function setQueryRows(queries) {
  el.queryRows().innerHTML = '';
  if (!queries || queries.length === 0) {
    addQueryRow();
    addQueryRow();
    return;
  }
  queries.forEach((q) => addQueryRow(q.emoji, q.titulo, q.query));
}

// ── Filters ──
function toggleFilters() {
  el.filtersPanel().classList.toggle('open');
}

async function loadFilterOptions() {
  try {
    const res = await fetch('/api/sessions');
    const data = await res.json();
    const select = document.getElementById('filter-session');
    data.sessions.forEach((s) => {
      const opt = document.createElement('option');
      opt.value = s.name;
      opt.textContent = `${s.name} (${s.count})`;
      select.appendChild(opt);
    });
  } catch (e) {
    console.warn('Error loading sessions:', e);
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

  // Render HTML in iframe
  el.resultsBody().srcdoc = data.html;
  el.resultsBody().style.minHeight = Math.max(500, window.innerHeight - 300) + 'px';

  // Store result path for download/copy
  el.resultsBody().dataset.path = data.path || '';
}

function filterResults() {
  const q = el.searchInput().value.toLowerCase();
  // For now, simply pass the filter query to the iframe
  // (full implementation would filter the iframe's DOM)
}

function newQuery() {
  setQueryRows([]);
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
      <div class="h-title">${escapeHtml(q.title)}</div>
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

    // If we have the HTML, load it
    if (q.result_path) {
      try {
        const htmlRes = await fetch(`/static/../${encodeURI(q.result_path)}`);
        // Actually we need to read the file... but the file might be outside static
        // So instead we'll use a workaround: restore the request and re-run
      } catch (e) {
        // File might not be accessible, re-run
      }
    }

    // Try to load full query details from the list or refetch
    // For now, just load the results from the file
    if (q.result_path) {
      // Use fetch to get the HTML file
      const htmlRes = await fetch(`/api/map-file?path=${encodeURIComponent(q.result_path)}`);
      if (htmlRes.ok) {
        const htmlData = await htmlRes.json();
        showResults({
          id: q.id,
          title: q.title,
          html: htmlData.html,
          stats: q.stats,
          path: q.result_path,
          created_at: q.created_at,
        });
        return;
      }
    }

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