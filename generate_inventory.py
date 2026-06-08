#!/usr/bin/env python3
"""Generate HTML inventory of all photo sessions with their configuration."""

import yaml
from pathlib import Path

BASE = Path("/media/dargonar/bkp_1t_new/portfolio/photos")
FNAME = "photor.session.yaml"

VALID = {'.jpg','.jpeg','.png','.webp','.bmp','.tiff','.tif',
         '.JPG','.JPEG','.PNG','.WEBP','.BMP','.TIFF','.TIF'}

def has_photos(d):
    return any(f.suffix.lower() in {e.lower() for e in VALID} for f in d.iterdir() if f.is_file())

def count_photos(d):
    return sum(1 for f in d.iterdir() if f.is_file() and f.suffix.lower() in {e.lower() for e in VALID})

def slugify(name):
    return name.lower().replace("_", "-").replace(" ", "-").replace("--", "-")

def walk_all(directory, depth=0):
    if directory.name.startswith('.'):
        return []
    results = []
    if has_photos(directory):
        yaml_path = directory / FNAME
        if yaml_path.exists():
            with open(yaml_path) as f:
                data = yaml.safe_load(f) or {}
        else:
            data = {}
        results.append({
            'path': str(directory.relative_to(BASE)),
            'depth': depth,
            'photos': count_photos(directory),
            'yaml': data,
        })
    for child in sorted(directory.iterdir()):
        if child.is_dir() and not child.name.startswith('.'):
            results.extend(walk_all(child, depth + 1))
    return results

# Collect all sessions
all_sessions = walk_all(BASE)

# Group by project
by_project = {}
for s in all_sessions:
    p = s['yaml'].get('project', s['yaml'].get('session', slugify(Path(s['path']).name)))
    if p not in by_project:
        by_project[p] = []
    by_project[p].append(s)

total_photos = sum(s['photos'] for s in all_sessions)

# ── Generate HTML ──

def fmt(v):
    if v is None:
        return ''
    s = str(v)
    if len(s) > 60:
        return s[:57] + '...'
    return s

def field_row(label, value):
    if value and str(value).strip():
        return f'<tr><td class="field">{label}</td><td>{fmt(value)}</td></tr>'
    return ''

html = f'''<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Inventario de Sesiones — photor</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0d0d0d; color: #e0e0e0; padding: 20px; }}
  h1 {{ font-size: 1.5em; margin-bottom: 4px; color: #fff; }}
  .subtitle {{ color: #888; margin-bottom: 24px; font-size: 0.9em; }}
  .project {{ margin-bottom: 32px; }}
  .project-header {{ background: #1a1a2e; padding: 10px 14px; border-radius: 8px 8px 0 0; font-weight: 600; font-size: 1.1em; display: flex; justify-content: space-between; color: #b388ff; }}
  .project-header .total {{ color: #888; font-weight: normal; }}
  .session {{ background: #1a1a1a; border-bottom: 1px solid #2a2a2a; }}
  .session:last-child {{ border-radius: 0 0 8px 8px; }}
  .session-path {{ padding: 10px 14px 4px; font-family: 'SF Mono', 'Fira Code', monospace; font-size: 0.85em; color: #64ffda; cursor: pointer; display: flex; justify-content: space-between; }}
  .session-path .count {{ color: #666; font-size: 0.85em; }}
  .session-fields {{ padding: 0 14px 10px; display: none; }}
  .session.folded .session-fields {{ display: none; }}
  .session.expanded .session-fields {{ display: block; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 0.82em; }}
  td {{ padding: 2px 8px; vertical-align: top; }}
  td.field {{ color: #888; width: 140px; white-space: nowrap; }}
  .tag {{ display: inline-block; background: #2d2d3d; color: #b388ff; padding: 1px 8px; border-radius: 10px; font-size: 0.8em; margin: 1px 2px; }}
  .media {{ color: #64ffda; font-size: 0.78em; word-break: break-all; }}
  .stats-bar {{ background: #1a1a2e; border-radius: 8px; padding: 14px; margin-bottom: 24px; display: flex; gap: 32px; flex-wrap: wrap; }}
  .stat {{ text-align: center; }}
  .stat-num {{ font-size: 1.8em; font-weight: 700; color: #b388ff; }}
  .stat-label {{ font-size: 0.78em; color: #666; }}
  input.search {{ width: 100%; padding: 10px 14px; background: #1a1a1a; border: 1px solid #333; border-radius: 8px; color: #e0e0e0; font-size: 0.9em; margin-bottom: 20px; outline: none; }}
  input.search:focus {{ border-color: #b388ff; }}
  .no-results {{ text-align: center; color: #666; padding: 40px; display: none; }}
</style>
</head>
<body>
<h1>📷 Inventario de Sesiones</h1>
<p class="subtitle">photor · todas las carpetas con fotos en <code>portfolio/photos/</code></p>

<div class="stats-bar">
  <div class="stat"><div class="stat-num">{len(all_sessions)}</div><div class="stat-label">sesiones</div></div>
  <div class="stat"><div class="stat-num">{len(by_project)}</div><div class="stat-label">proyectos</div></div>
  <div class="stat"><div class="stat-num">{total_photos:,}</div><div class="stat-label">fotos</div></div>
</div>

<input type="text" class="search" id="search" placeholder="Filtrar por proyecto, sesión, persona, tags..." oninput="filterSessions()">

<div id="projects">
'''

for proj in sorted(by_project):
    sessions = by_project[proj]
    proj_total = sum(s['photos'] for s in sessions)
    proj_slug = slugify(proj)
    html += f'<div class="project" data-project="{proj_slug}">\n'
    html += f'<div class="project-header"><span>{proj}</span><span class="total">{len(sessions)} sesiones · {proj_total:,} fotos</span></div>\n'
    for s in sessions:
        y = s['yaml']
        path = s['path']
        name = Path(path).name
        depth = s['depth']
        indent = depth * 20
        has_yaml = bool(y)
        
        session_name = y.get('session', slugify(name))
        session_set = y.get('set', 'default')
        
        html += f'<div class="session" data-path="{path}" data-session="{yaml.dump(y, allow_unicode=True)}">\n'
        html += f'<div class="session-path" onclick="toggleSession(this)" style="padding-left:{14 + indent}px">'
        html += f'<span>📁 {path} <span class="tag" style="background:#333;color:#999">{session_set}</span></span>'
        html += f'<span class="count">{s["photos"]} fotos</span>'
        html += f'</div>\n'
        html += f'<div class="session-fields" style="padding-left:{14 + indent}px">\n'
        html += '<table>\n'
        
        def tagify(v):
            if not v:
                return ''
            return ' '.join(f'<span class="tag">{t.strip()}</span>' for t in str(v).split(',') if t.strip())
        
        html += field_row('session', session_name)
        html += field_row('set', session_set)
        html += field_row('project', y.get('project', ''))
        html += field_row('personajes', tagify(y.get('personajes', '')))
        html += field_row('tags', tagify(y.get('tags', '')))
        html += field_row('location', y.get('location', ''))
        html += field_row('year', y.get('year', ''))
        html += field_row('description', y.get('description', ''))
        html += field_row('selected', y.get('selected', ''))
        html += field_row('rating', y.get('rating', ''))
        html += field_row('original_location', y.get('original_location', ''))
        
        html += '</table>\n'
        html += '</div>\n'
        html += '</div>\n'
    html += '</div>\n'

html += '''</div>

<div class="no-results" id="no-results">😕 No se encontraron sesiones</div>

<script>
function toggleSession(el) {
  const session = el.parentElement;
  session.classList.toggle('expanded');
}

function filterSessions() {
  const q = document.getElementById('search').value.toLowerCase().normalize('NFD').replace(/[\\u0300-\\u036f]/g, '');
  const projects = document.querySelectorAll('.project');
  let visible = 0;
  
  projects.forEach(proj => {
    const sessions = proj.querySelectorAll('.session');
    let projVisible = 0;
    
    sessions.forEach(s => {
      const text = s.getAttribute('data-path') + ' ' + s.getAttribute('data-session');
      const match = text.toLowerCase().normalize('NFD').replace(/[\\u0300-\\u036f]/g, '').includes(q);
      s.style.display = match ? '' : 'none';
      if (match) projVisible++;
    });
    
    proj.style.display = projVisible > 0 ? '' : 'none';
    visible += projVisible;
  });
  
  document.getElementById('no-results').style.display = visible > 0 ? 'none' : 'block';
}

// Expand all by default on desktop
if (window.innerWidth > 768) {
  document.querySelectorAll('.session').forEach(s => s.classList.add('expanded'));
}
</script>
</body>
</html>'''

output_path = BASE / "inventario.html"
with open(output_path, "w") as f:
    f.write(html)

print(f"✅ Inventario generado: {output_path}")
print(f"   {len(all_sessions)} sesiones · {len(by_project)} proyectos · {total_photos:,} fotos")