from __future__ import annotations

import json
import os
import tempfile
from typing import List, Dict, Any

from flask import Flask, request, redirect, url_for, render_template_string, abort

app = Flask(__name__)

# Data persistence (simple JSON file stored alongside this script)
DATA_FILE = os.path.join(os.path.dirname(__file__), "todo_data.json")


def ensure_data_file() -> None:
    if not os.path.exists(DATA_FILE):
        atomic_write_json(DATA_FILE, {"next_id": 1, "items": []})


def atomic_write_json(path: str, data: Dict[str, Any]) -> None:
    # Write atomically to reduce the risk of file corruption
    directory = os.path.dirname(path)
    fd, tmp_path = tempfile.mkstemp(dir=directory, prefix="._tmp_todo_", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, path)
    finally:
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except OSError:
            pass


def load_data() -> Dict[str, Any]:
    ensure_data_file()
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        # Reset corrupted file
        data = {"next_id": 1, "items": []}
        atomic_write_json(DATA_FILE, data)
        return data


def save_data(data: Dict[str, Any]) -> None:
    atomic_write_json(DATA_FILE, data)


def _get_items() -> List[Dict[str, Any]]:
    return load_data()["items"]


PAGE_HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Todo</title>
  <style>
    :root {
      --bg: #ffffff;
      --fg: #111111;
      --muted: #6b7280;
      --border: #e5e7eb;
      --accent: #111111;
      --accent-contrast: #ffffff;
    }
    html, body { height: 100%; }
    body {
      margin: 0;
      font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, "Apple Color Emoji", "Segoe UI Emoji";
      background: var(--bg);
      color: var(--fg);
      display: grid;
      place-items: start center;
    }
    .container {
      width: min(680px, 92vw);
      margin-top: 8vh;
    }
    header { margin-bottom: 1.25rem; }
    h1 {
      font-size: clamp(1.75rem, 3.2vw, 2.25rem);
      margin: 0 0 .25rem 0;
      letter-spacing: -0.02em;
    }
    .sub { color: var(--muted); font-size: .95rem; }

    form.add {
      display: grid;
      grid-template-columns: 1fr auto;
      gap: .5rem;
      margin: 1rem 0 1.25rem 0;
    }
    input[type=text] {
      font: inherit;
      padding: .8rem .9rem;
      border: 1px solid var(--border);
      border-radius: .5rem;
      outline: none;
    }
    input[type=text]:focus { border-color: #9ca3af; }
    button {
      font: inherit;
      padding: .8rem 1rem;
      border-radius: .5rem;
      border: 1px solid var(--accent);
      background: var(--accent);
      color: var(--accent-contrast);
      cursor: pointer;
    }
    button.secondary {
      background: transparent;
      color: var(--fg);
      border-color: var(--border);
    }

    ul { list-style: none; padding: 0; margin: 0; }
    li.item {
      display: grid;
      grid-template-columns: auto 1fr auto;
      align-items: center;
      gap: .75rem;
      padding: .75rem;
      border: 1px solid var(--border);
      border-radius: .5rem;
      margin-bottom: .5rem;
    }
    .text { line-height: 1.35; }
    .done .text { text-decoration: line-through; color: var(--muted); }
    .controls { display: inline-flex; gap: .4rem; }
    .empty { color: var(--muted); text-align: center; padding: 2rem 0; border: 2px dashed var(--border); border-radius: .75rem; }
    footer { margin-top: 1rem; display:flex; justify-content: space-between; align-items: center; color: var(--muted); font-size: .9rem; }
    a { color: inherit; }
  </style>
</head>
<body>
  <main class="container">
    <header>
      <h1>Todo</h1>
      <div class="sub">A tiny list you can check off.</div>
    </header>

    <form class="add" action="{{ url_for('add') }}" method="post" autocomplete="off">
      <input type="text" name="text" placeholder="Add a task…" minlength="1" maxlength="200" required>
      <button type="submit">Add</button>
    </form>

    {% if items %}
      <ul>
        {% for it in items %}
          <li class="item {% if it.done %}done{% endif %}">
            <form action="{{ url_for('toggle', item_id=it.id) }}" method="post" style="margin:0;">
              <input type="checkbox" aria-label="Toggle done" onclick="this.form.submit()" {% if it.done %}checked{% endif %}>
            </form>
            <div class="text">{{ it.text }}</div>
            <div class="controls">
              <form action="{{ url_for('delete', item_id=it.id) }}" method="post" style="margin:0;">
                <button type="submit" class="secondary" title="Delete">Delete</button>
              </form>
            </div>
          </li>
        {% endfor %}
      </ul>
    {% else %}
      <div class="empty">Nothing here yet. Add your first task above.</div>
    {% endif %}

    <footer>
      <div>{{ items|length }} item{{ '' if items|length == 1 else 's' }}</div>
      <form action="{{ url_for('clear_completed') }}" method="post" style="margin:0;">
        <button type="submit" class="secondary">Clear completed</button>
      </form>
    </footer>
  </main>
</body>
</html>
"""


@app.route("/", methods=["GET"])
def index():
    data = load_data()
    items = data.get("items", [])
    # sort by id (the oldest first)
    items = sorted(items, key=lambda x: x["id"])  # type: ignore[index]
    return render_template_string(PAGE_HTML, items=items)


@app.route("/add", methods=["POST"])
def add():
    text = (request.form.get("text") or "").strip()
    if not text:
        return redirect(url_for("index"))
    data = load_data()
    next_id = int(data.get("next_id", 1))
    item = {"id": next_id, "text": text[:200], "done": False}
    data["items"].append(item)
    data["next_id"] = next_id + 1
    save_data(data)
    return redirect(url_for("index"))


@app.route("/toggle/<int:item_id>", methods=["POST"])
def toggle(item_id: int):
    data = load_data()
    found = False
    for it in data["items"]:
        if it["id"] == item_id:
            it["done"] = not bool(it.get("done"))
            found = True
            break
    if not found:
        abort(404)
    save_data(data)
    return redirect(url_for("index"))


@app.route("/delete/<int:item_id>", methods=["POST"])
def delete(item_id: int):
    data = load_data()
    before = len(data["items"])
    data["items"] = [it for it in data["items"] if it["id"] != item_id]
    after = len(data["items"])
    if before == after:
        abort(404)
    save_data(data)
    return redirect(url_for("index"))


@app.route("/clear-completed", methods=["POST"])
def clear_completed():
    data = load_data()
    data["items"] = [it for it in data["items"] if not it.get("done")]
    save_data(data)
    return redirect(url_for("index"))


# Back-compat with url_for name used in the template
clear_completed.methods = {"POST"}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(debug=True, port=port)
