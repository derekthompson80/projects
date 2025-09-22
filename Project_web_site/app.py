from __future__ import annotations

import os
from pathlib import Path
from typing import List, Dict
from flask import Flask, render_template, abort, send_from_directory, url_for, redirect

# Base directory: country\projects
PROJECTS_ROOT = Path(__file__).resolve().parents[1]

app = Flask(__name__)


def list_projects() -> List[Dict[str, str]]:
    """Return a list of immediate subdirectories in PROJECTS_ROOT excluding this site.
    Each item: {name, path}
    """
    items: List[Dict[str, str]] = []
    for child in sorted(PROJECTS_ROOT.iterdir(), key=lambda p: p.name.lower()):
        if not child.is_dir():
            continue
        if child.name.startswith('.'):
            continue
        if child.name == 'Project_web_site':
            continue
        items.append({
            'name': child.name,
            'path': str(child)
        })
    return items


def scan_project(name: str, base_rel: str = '', max_depth: int = 2, max_entries: int = 500) -> Dict:
    """Scan a project directory (or subdirectory) to a limited depth and collect file info.
    Returns a dict with project path, current base path, entries, and detected entry_points (only at root).

    base_rel: subdirectory within the project to browse (relative to project root).
    """
    project_root = PROJECTS_ROOT / name
    if not project_root.exists() or not project_root.is_dir():
        abort(404)

    base_root = (project_root / base_rel).resolve() if base_rel else project_root
    try:
        base_root.relative_to(project_root)
    except Exception:
        abort(403)
    if not base_root.exists() or not base_root.is_dir():
        abort(404)

    entries: List[Dict] = []
    entry_points: List[Dict[str, str]] = []

    # Identify common entry files at top level and one level deep (only when at project root)
    candidates = {'app.py', 'main.py', 'run.py'}
    find_entry_points = (base_root == project_root)

    def rel(p: Path) -> str:
        try:
            return str(p.relative_to(base_root))
        except Exception:
            return p.name

    def rel_from_project(p: Path) -> str:
        try:
            return str(p.relative_to(project_root))
        except Exception:
            return p.name

    def is_text_file(p: Path) -> bool:
        # naive check by extension
        return p.suffix.lower() in {
            '.py', '.txt', '.md', '.json', '.yaml', '.yml', '.html', '.css', '.js', '.ini', '.cfg', '.toml', '.csv'
        }

    def walk(current: Path, depth: int = 0):
        nonlocal entries, entry_points
        if depth > max_depth:
            return
        try:
            children = sorted(current.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        except Exception:
            return
        for ch in children:
            if len(entries) >= max_entries:
                return
            if ch.name.startswith('.'):
                continue
            info = {
                'name': ch.name,
                'rel': rel(ch),  # relative to the current base
                'rel_from_project': rel_from_project(ch),  # full relative from project root
                'is_dir': ch.is_dir(),
                'size': ch.stat().st_size if ch.is_file() else None,
                'can_view': (ch.is_file() and is_text_file(ch)),
            }
            entries.append(info)
            if find_entry_points:
                if ch.is_file() and (ch.name in candidates) and (ch.parent == project_root or (ch.parent.parent == project_root if ch.parent != project_root else False)):
                    entry_points.append({
                        'name': ch.name,
                        'rel': rel_from_project(ch),
                    })
            if ch.is_dir():
                walk(ch, depth + 1)

    walk(base_root, 0)

    # Remove duplicates in entry_points while preserving order
    seen = set()
    unique_eps = []
    for ep in entry_points:
        key = ep['rel']
        if key not in seen:
            seen.add(key)
            unique_eps.append(ep)

    return {
        'project_root': str(project_root),
        'base_root': str(base_root),
        'base_rel': base_rel,
        'entries': entries,
        'entry_points': unique_eps,
    }


@app.route('/')
def index():
    projects = list_projects()
    return render_template('index.html', projects=projects)


@app.route('/project/<name>')
def project_detail(name: str):
    data = scan_project(name)
    return render_template('project.html', name=name, data=data)


@app.route('/project/<name>/browse/<path:relpath>')
def browse_subdir(name: str, relpath: str):
    # View contents of a subdirectory within the project
    data = scan_project(name, base_rel=relpath)
    return render_template('project.html', name=name, data=data)


@app.route('/project/<name>/view/<path:relpath>')
def view_file(name: str, relpath: str):
    # Serve only safe, text-like files from inside the project directory
    root = PROJECTS_ROOT / name
    # Normalize path and ensure it stays within root
    safe_path = (root / relpath).resolve()
    if not safe_path.exists() or not safe_path.is_file():
        abort(404)
    try:
        safe_path.relative_to(root)
    except Exception:
        abort(403)

    # Read and render as text in a template (avoid send_file for simplicity)
    try:
        # Use utf-8 with fallback
        try:
            content = safe_path.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            content = safe_path.read_text(encoding='latin-1')
    except Exception:
        abort(403)
    return render_template('view_file.html', name=name, relpath=relpath, content=content)


# Optional: static passthrough for known static-only mini-sites
@app.route('/project/<name>/static/<path:relpath>')
def project_static(name: str, relpath: str):
    # This allows linking to static assets under a project's "static" dir
    root = PROJECTS_ROOT / name / 'static'
    if not root.exists() or not root.is_dir():
        abort(404)
    return send_from_directory(root, relpath)


@app.route('/project/<name>/open')
def open_project_folder(name: str):
    # Attempt to open the folder in the system file explorer (Windows: Explorer)
    path = PROJECTS_ROOT / name
    if not path.exists() or not path.is_dir():
        abort(404)
    try:
        # Windows-specific; harmless no-op if not supported
        os.startfile(str(path))  # type: ignore[attr-defined]
    except Exception:
        # Silently ignore if cannot open
        pass
    return redirect(url_for('project_detail', name=name))


if __name__ == '__main__':
    # Run this site on a non-conflicting port if desired
    app.run(debug=True)  # default 5000
