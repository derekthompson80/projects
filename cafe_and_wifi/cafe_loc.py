import os
import sqlite3
from typing import Any, Dict, List, Optional, Tuple

from flask import Flask, jsonify, request, render_template_string, redirect, url_for

app = Flask(__name__)

# Path to the SQLite database (cafes.db should be in the same folder as this file)
DB_PATH = os.path.join(os.path.dirname(__file__), "cafes.db")


# ----------------------
# Database helper methods
# ----------------------

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def guess_cafes_table_name(conn: sqlite3.Connection) -> str:
    # Prefer a table explicitly named 'cafes' if present; otherwise, pick the first table containing 'caf'
    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    names = [r[0] for r in cur.fetchall()]
    if "cafes" in names:
        return "cafes"
    for n in names:
        if "caf" in n.lower():
            return n
    # Fallback to the first table, if any
    if names:
        return names[0]
    raise RuntimeError("No tables found in cafes.db. Please ensure the database is initialized.")


def get_table_info(conn: sqlite3.Connection, table: str) -> List[Dict[str, Any]]:
    cur = conn.execute(f"PRAGMA table_info({table})")
    cols = []
    for r in cur.fetchall():
        # PRAGMA table_info returns: cid, name, type, notnull, dflt_value, pk
        cols.append({
            "cid": r[0],
            "name": r[1],
            "type": (r[2] or "").upper(),
            "notnull": bool(r[3]),
            "default": r[4],
            "pk": bool(r[5]),
        })
    return cols


def get_pk_column(columns: List[Dict[str, Any]]) -> str:
    for c in columns:
        if c.get("pk"):
            return c["name"]
    # Common fallback
    return "id"


def parse_bool(val: Optional[str]) -> Optional[int]:
    if val is None:
        return None
    s = str(val).strip().lower()
    if s in ("1", "true", "yes", "y", "on"):
        return 1
    if s in ("0", "false", "no", "n", "off"):
        return 0
    return None


def is_boolish_column(name: str, col_type: str) -> bool:
    # Heuristic: columns starting with 'has_' or INT columns that typically store 0/1
    if name.lower().startswith("has_"):
        return True
    return col_type in ("BOOL", "BOOLEAN")


def row_to_dict(row: sqlite3.Row, columns: List[Dict[str, Any]]) -> Dict[str, Any]:
    d: Dict[str, Any] = {}
    for c in columns:
        name = c["name"]
        val = row[name]
        if is_boolish_column(name, c["type"]):
            # Interpret 0/1 and truthy strings to booleans in the API response
            if val is None:
                d[name] = None
            else:
                try:
                    d[name] = bool(int(val))
                except Exception:
                    d[name] = bool(val)
        else:
            d[name] = val
    return d


def build_filters(params: Dict[str, str], columns: List[Dict[str, Any]]) -> Tuple[str, List[Any]]:
    allowed = {c["name"]: c for c in columns}
    sql_parts: List[str] = []
    args: List[Any] = []

    # Simple text search on name/location if provided via ?q=... (case-insensitive LIKE)
    q = params.get("q")
    if q:
        q_like = f"%{q}%"
        if "name" in allowed and "location" in allowed:
            sql_parts.append("(LOWER(name) LIKE LOWER(?) OR LOWER(location) LIKE LOWER(?))")
            args.extend([q_like, q_like])
        elif "name" in allowed:
            sql_parts.append("LOWER(name) LIKE LOWER(?)")
            args.append(q_like)
        elif "location" in allowed:
            sql_parts.append("LOWER(location) LIKE LOWER(?)")
            args.append(q_like)

    # Column-specific filters by equality, including boolean handling for has_* columns
    for key, value in params.items():
        if key in ("q",):
            continue
        if key in allowed:
            col = allowed[key]
            if is_boolish_column(key, col["type"]):
                b = parse_bool(value)
                if b is not None:
                    sql_parts.append(f"{key} = ?")
                    args.append(b)
            else:
                # exact match
                sql_parts.append(f"{key} = ?")
                args.append(value)

    where = (" WHERE " + " AND ".join(sql_parts)) if sql_parts else ""
    return where, args


# ----------------------
# REST API endpoints
# ----------------------

@app.route("/api/cafes", methods=["GET"])
def list_cafes():
    with get_connection() as conn:
        table = guess_cafes_table_name(conn)
        columns = get_table_info(conn, table)
        where, args = build_filters(request.args.to_dict(), columns)
        sql = f"SELECT * FROM {table}{where} ORDER BY {get_pk_column(columns)} ASC"
        rows = conn.execute(sql, args).fetchall()
        data = [row_to_dict(r, columns) for r in rows]
        return jsonify({"cafes": data, "count": len(data)})


@app.route("/api/cafes/<int:item_id>", methods=["GET"])
def get_cafe(item_id: int):
    with get_connection() as conn:
        table = guess_cafes_table_name(conn)
        columns = get_table_info(conn, table)
        pk = get_pk_column(columns)
        row = conn.execute(f"SELECT * FROM {table} WHERE {pk} = ?", (item_id,)).fetchone()
        if not row:
            return jsonify({"error": "Cafe not found"}), 404
        return jsonify(row_to_dict(row, columns))


@app.route("/api/cafes", methods=["POST"])
def add_cafe():
    payload = request.get_json(silent=True) or {}
    if not payload and request.form:
        payload = request.form.to_dict()
    with get_connection() as conn:
        table = guess_cafes_table_name(conn)
        columns = get_table_info(conn, table)
        col_map = {c["name"]: c for c in columns}
        pk = get_pk_column(columns)

        # Remove primary key if present in payload (usually autoincrement)
        if pk in payload:
            payload.pop(pk, None)

        # Only include known, non-PK columns
        insert_cols: List[str] = []
        insert_vals: List[Any] = []
        placeholders: List[str] = []
        for name, col in col_map.items():
            if name == pk:
                continue
            if name in payload:
                val = payload[name]
                if is_boolish_column(name, col["type"]):
                    b = parse_bool(val)
                    val = 1 if b is None and str(val).strip() not in ("", "0") else (b if b is not None else 0)
                insert_cols.append(name)
                insert_vals.append(val)
                placeholders.append("?")

        if not insert_cols:
            return jsonify({"error": "No valid fields provided"}), 400

        sql = f"INSERT INTO {table} (" + ",".join(insert_cols) + ") VALUES (" + ",".join(placeholders) + ")"
        cur = conn.execute(sql, insert_vals)
        conn.commit()
        new_id = cur.lastrowid

    return jsonify({"message": "Cafe added", "id": new_id}), 201


@app.route("/api/cafes/<int:item_id>", methods=["PATCH", "PUT"])
def update_cafe(item_id: int):
    payload = request.get_json(silent=True) or {}
    if not payload and request.form:
        payload = request.form.to_dict()
    with get_connection() as conn:
        table = guess_cafes_table_name(conn)
        columns = get_table_info(conn, table)
        col_map = {c["name"]: c for c in columns}
        pk = get_pk_column(columns)

        # Ensure row exists
        exists = conn.execute(f"SELECT 1 FROM {table} WHERE {pk} = ?", (item_id,)).fetchone()
        if not exists:
            return jsonify({"error": "Cafe not found"}), 404

        sets: List[str] = []
        args: List[Any] = []
        for name, col in col_map.items():
            if name == pk:
                continue
            if name in payload:
                val = payload[name]
                if is_boolish_column(name, col["type"]):
                    b = parse_bool(val)
                    val = 1 if b is None and str(val).strip() not in ("", "0") else (b if b is not None else 0)
                sets.append(f"{name} = ?")
                args.append(val)
        if not sets:
            return jsonify({"error": "No updatable fields provided"}), 400

        args.append(item_id)
        conn.execute(f"UPDATE {table} SET " + ", ".join(sets) + f" WHERE {pk} = ?", args)
        conn.commit()
        return jsonify({"message": "Cafe updated", "id": item_id})


@app.route("/api/cafes/<int:item_id>", methods=["DELETE"])
def delete_cafe(item_id: int):
    with get_connection() as conn:
        table = guess_cafes_table_name(conn)
        columns = get_table_info(conn, table)
        pk = get_pk_column(columns)
        cur = conn.execute(f"DELETE FROM {table} WHERE {pk} = ?", (item_id,))
        conn.commit()
        if cur.rowcount == 0:
            return jsonify({"error": "Cafe not found"}), 404
        return jsonify({"message": "Cafe deleted", "id": item_id})


# ----------------------
# Minimal Web UI (HTML)
# ----------------------

INDEX_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Laptop Friendly – London Style Cafes</title>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css">
  <style>
    :root{
      --lf-bg:#0f131a; --lf-card:#151a22; --lf-accent:#00d1b2; --lf-muted:#8b95a7;
      --lf-badge:#1e2836; --lf-yes:#1e3b2f; --lf-no:#3b1e1e; --lf-yes-text:#3ddc97; --lf-no-text:#ff6b6b;
    }
    body{background:var(--lf-bg); color:#e9eef5;}
    a{color:#9ad0ff}
    header{padding:2rem 0 1rem}
    .brand{font-weight:700; letter-spacing:.3px}
    .subtle{color:var(--lf-muted)}
    .filters{background:var(--lf-card); border-radius:.75rem; padding:1rem}
    .card{background:var(--lf-card); border:none; box-shadow:0 0 0 1px rgba(255,255,255,.04);}
    .card-img-top{height:180px; object-fit:cover}
    .badge-soft{background:var(--lf-badge); color:#cfd6e4}
    .feat{font-size:.8rem}
    .feat .yes{background:var(--lf-yes); color:var(--lf-yes-text)}
    .feat .no{background:var(--lf-no); color:var(--lf-no-text)}
    .btn-outline-danger{--bs-btn-hover-bg:#dc3545; --bs-btn-hover-color:#fff}
    footer{color:var(--lf-muted); font-size:.9rem; padding:2rem 0}
    .add-form{background:var(--lf-card); border-radius:.75rem; padding:1rem}
  </style>
</head>
<body>
  <div class="container">
    <header class="d-flex align-items-center justify-content-between">
      <div>
        <h1 class="brand mb-1">Laptop Friendly – London</h1>
        <div class="subtle">Find cafes great for working: WiFi, power sockets, calls, and more.</div>
      </div>
      <div>
        <a class="btn btn-outline-light" href="{{ url_for('index') }}">Home</a>
      </div>
    </header>

    <form class="filters mb-4" method="get" action="{{ url_for('index') }}">
      <div class="row g-3 align-items-end">
        <div class="col-12 col-md-4">
          <label class="form-label subtle">Search</label>
          <input type="text" name="q" value="{{ request.args.get('q', '') }}" class="form-control" placeholder="Search name or area">
        </div>
        {% if 'location' in column_names %}
        <div class="col-12 col-md-3">
          <label class="form-label subtle">Area</label>
          <select class="form-select" name="location">
            <option value="">All</option>
            {% for loc in locations %}
              <option value="{{ loc }}" {% if request.args.get('location') == loc %}selected{% endif %}>{{ loc }}</option>
            {% endfor %}
          </select>
        </div>
        {% endif %}
        <div class="col-6 col-md-1 form-check">
          {% if 'has_wifi' in column_names %}
          <input class="form-check-input" type="checkbox" name="has_wifi" id="has_wifi" value="1" {% if request.args.get('has_wifi') in ('1','true','on') %}checked{% endif %}>
          <label class="form-check-label subtle" for="has_wifi">WiFi</label>
          {% endif %}
        </div>
        <div class="col-6 col-md-1 form-check">
          {% if 'has_sockets' in column_names %}
          <input class="form-check-input" type="checkbox" name="has_sockets" id="has_sockets" value="1" {% if request.args.get('has_sockets') in ('1','true','on') %}checked{% endif %}>
          <label class="form-check-label subtle" for="has_sockets">Sockets</label>
          {% endif %}
        </div>
        <div class="col-6 col-md-1 form-check">
          {% if 'has_toilet' in column_names %}
          <input class="form-check-input" type="checkbox" name="has_toilet" id="has_toilet" value="1" {% if request.args.get('has_toilet') in ('1','true','on') %}checked{% endif %}>
          <label class="form-check-label subtle" for="has_toilet">Toilet</label>
          {% endif %}
        </div>
        <div class="col-6 col-md-1 form-check">
          {% if 'can_take_calls' in column_names %}
          <input class="form-check-input" type="checkbox" name="can_take_calls" id="can_take_calls" value="1" {% if request.args.get('can_take_calls') in ('1','true','on') %}checked{% endif %}>
          <label class="form-check-label subtle" for="can_take_calls">Calls</label>
          {% endif %}
        </div>
        <div class="col-12 col-md-1 text-md-end">
          <button type="submit" class="btn btn-primary w-100">Filter</button>
        </div>
      </div>
      <div class="mt-2">
        <a class="link-light subtle" href="{{ url_for('index') }}">Reset filters</a>
      </div>
    </form>

    <div class="row row-cols-1 row-cols-md-2 row-cols-lg-3 g-4 mb-5">
      {% for row in cafes %}
      <div class="col">
        <div class="card h-100">
          {% set img = row.get('img_url') or row.get('img_URL') %}
          <img class="card-img-top" src="{{ img or 'https://placehold.co/600x400?text=Cafe' }}" alt="{{ row.get('name') }} image" loading="lazy">
          <div class="card-body d-flex flex-column">
            <div class="d-flex justify-content-between align-items-start mb-1">
              <h5 class="card-title mb-0">
                {% set link = row.get('map_url') or row.get('map_URL') %}
                {% if link %}
                  <a href="{{ link }}" target="_blank" rel="noopener" class="stretched-link text-decoration-none text-light">{{ row.get('name') }}</a>
                {% else %}
                  {{ row.get('name') }}
                {% endif %}
              </h5>
              {% if 'location' in column_names %}
              <span class="badge badge-soft ms-2">{{ row.get('location') }}</span>
              {% endif %}
            </div>

            <div class="d-flex flex-wrap gap-2 feat mb-2">
              {% if 'has_wifi' in column_names %}
                <span class="badge {% if row.get('has_wifi') in (1, True, '1', 'Yes', 'yes') %}yes{% else %}no{% endif %}">WiFi</span>
              {% endif %}
              {% if 'has_sockets' in column_names %}
                <span class="badge {% if row.get('has_sockets') in (1, True, '1', 'Yes', 'yes') %}yes{% else %}no{% endif %}">Sockets</span>
              {% endif %}
              {% if 'has_toilet' in column_names %}
                <span class="badge {% if row.get('has_toilet') in (1, True, '1', 'Yes', 'yes') %}yes{% else %}no{% endif %}">Toilets</span>
              {% endif %}
              {% if 'can_take_calls' in column_names %}
                <span class="badge {% if row.get('can_take_calls') in (1, True, '1', 'Yes', 'yes') %}yes{% else %}no{% endif %}">Calls</span>
              {% endif %}
            </div>

            <div class="d-flex gap-3 mb-3 subtle">
              {% if 'seats' in column_names %}
                <div>Seats: <strong class="text-light">{{ row.get('seats') }}</strong></div>
              {% endif %}
              {% if 'coffee_price' in column_names %}
                <div>Coffee: <strong class="text-light">{{ row.get('coffee_price') }}</strong></div>
              {% endif %}
            </div>

            <div class="mt-auto d-flex gap-2">
              <form method="post" action="{{ url_for('web_delete', item_id=row[pk]) }}" onsubmit="return confirm('Delete this cafe?');">
                <button type="submit" class="btn btn-sm btn-outline-danger">Delete</button>
              </form>
            </div>
          </div>
        </div>
      </div>
      {% endfor %}
      {% if cafes|length == 0 %}
      <div class="col"><div class="alert alert-dark">No cafes match your filters.</div></div>
      {% endif %}
    </div>

    <section class="add-form mb-5">
      <h2 class="mb-3">Add a New Cafe</h2>
      <form class="row g-3" method="post" action="{{ url_for('web_add') }}">
        {% for c in columns if not c.pk %}
          <div class="col-md-6">
            <label class="form-label subtle">{{ c.name }}</label>
            {% if c.name.lower().startswith('has_') %}
              <div class="form-check">
                <input class="form-check-input" type="checkbox" name="{{ c.name }}" value="1" id="{{ c.name }}">
                <label class="form-check-label" for="{{ c.name }}">Yes</label>
              </div>
            {% else %}
              <input class="form-control" name="{{ c.name }}" placeholder="{{ c.type }}">
            {% endif %}
          </div>
        {% endfor %}
        <div class="col-12">
          <button type="submit" class="btn btn-success">Add Cafe</button>
        </div>
      </form>
    </section>

    <footer class="text-center">
      Inspired by laptopfriendly.co/london. This is a demo using your local cafes.db.
    </footer>
  </div>
</body>
</html>
"""


@app.route("/", methods=["GET"])
def index():
    # Populate card grid and filters using current query params
    with get_connection() as conn:
        table = guess_cafes_table_name(conn)
        columns = get_table_info(conn, table)
        pk = get_pk_column(columns)
        where, args = build_filters(request.args.to_dict(), columns)
        rows = conn.execute(f"SELECT * FROM {table}{where} ORDER BY {pk} ASC", args).fetchall()
        cafes = []
        for r in rows:
            cafes.append({c["name"]: r[c["name"]] for c in columns})
        # Distinct locations for filter dropdown (if column exists)
        col_names = [c["name"] for c in columns]
        locations: List[str] = []
        if "location" in col_names:
            loc_rows = conn.execute(f"SELECT DISTINCT location FROM {table} WHERE location IS NOT NULL ORDER BY location").fetchall()
            locations = [lr[0] for lr in loc_rows]
        return render_template_string(
            INDEX_TEMPLATE,
            columns=columns,
            cafes=cafes,
            pk=pk,
            column_names=col_names,
            locations=locations,
        )


@app.route("/web/add", methods=["POST"])
def web_add():
    # Proxy to API insert using form fields
    form_data = request.form.to_dict()
    # Convert unchecked checkboxes for has_* to 0 explicitly if those columns exist
    with get_connection() as conn:
        table = guess_cafes_table_name(conn)
        columns = get_table_info(conn, table)
        bool_cols = {c["name"] for c in columns if c["name"].lower().startswith("has_")}
        for bc in bool_cols:
            if bc not in form_data:
                form_data[bc] = "0"
    with app.test_request_context(json=form_data):
        # Call the same logic as API but without performing an internal request
        payload = form_data
    # Actually insert directly to DB to avoid nested request contexts
    with get_connection() as conn:
        table = guess_cafes_table_name(conn)
        columns = get_table_info(conn, table)
        col_map = {c["name"]: c for c in columns}
        pk = get_pk_column(columns)

        if pk in payload:
            payload.pop(pk, None)

        insert_cols: List[str] = []
        insert_vals: List[Any] = []
        placeholders: List[str] = []
        for name, col in col_map.items():
            if name == pk:
                continue
            if name in payload:
                val = payload[name]
                if is_boolish_column(name, col["type"]):
                    b = parse_bool(val)
                    val = 1 if b is None and str(val).strip() not in ("", "0") else (b if b is not None else 0)
                insert_cols.append(name)
                insert_vals.append(val)
                placeholders.append("?")
        if insert_cols:
            conn.execute(
                f"INSERT INTO {table} (" + ",".join(insert_cols) + ") VALUES (" + ",".join(placeholders) + ")",
                insert_vals,
            )
            conn.commit()
    return redirect(url_for("index"))


@app.route("/web/delete/<int:item_id>", methods=["POST"]) 
def web_delete(item_id: int):
    with get_connection() as conn:
        table = guess_cafes_table_name(conn)
        columns = get_table_info(conn, table)
        pk = get_pk_column(columns)
        conn.execute(f"DELETE FROM {table} WHERE {pk} = ?", (item_id,))
        conn.commit()
    return redirect(url_for("index"))


# --------------
# App Entrypoint
# --------------
if __name__ == "__main__":
    if not os.path.exists(DB_PATH):
        raise SystemExit(f"Database not found at {DB_PATH}. Please ensure cafes.db is present.")
    # Run the Flask development server
    app.run(host="127.0.0.1", port=5000, debug=True)



@app.route("/london", methods=["GET"])
def london():
    # Serve the same view; path provided to mimic laptopfriendly.co/london
    return index()
