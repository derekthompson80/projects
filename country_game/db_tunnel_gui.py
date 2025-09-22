
"""
DB Tunnel GUI — Tkinter desktop app to connect to spade605$county_game_server via SSH tunnel

How to run (from repo root):
  - python -m projects.country_game.db_tunnel_gui
    or
  - python projects\country_game\db_tunnel_gui.py

This GUI uses the existing SSH tunnel helper at
projects.country_game.country_game_utilites.ssh_db_tunnel to open an SSH
port-forward and then connect to the MySQL database. It provides:
- Connect / Disconnect buttons
- Status panel showing connection info
- List Tables button to show tables in the database
- A simple query runner (SELECT only) with results printed below

Notes:
- This tool depends on Paramiko, sshtunnel, and a MySQL driver (mysqlclient).
  If those are not installed, the app will show a friendly message with
  installation hints instead of crashing.
- The SSH and DB credentials are taken from the ssh_db_tunnel module, which
  is already configured for spade605$county_game_server.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import queue
import time
import importlib
from typing import Optional, Any

# --- Helper functions (module-level) for testability ---

def normalize_table_list(rows) -> list[str]:
    """Normalize results of SHOW TABLES into a list of table-name strings.
    Accepts rows like [("name",), (b"bytes",)] or ["name"] etc.
    """
    tables: list[str] = []
    try:
        for r in (rows or []):
            if isinstance(r, (list, tuple)) and r:
                val = r[0]
            else:
                val = r
            if isinstance(val, (bytes, bytearray)):
                try:
                    val = val.decode("utf-8", errors="ignore")
                except Exception:
                    val = str(val)
            tables.append(str(val))
    except Exception:
        pass
    return tables


def build_update_sql(table: str,
                     columns: list[str],
                     original_row: tuple,
                     target_col: str,
                     new_value: object) -> tuple[str, list]:
    """Build a parameterized UPDATE statement that sets target_col to new_value
    using a WHERE clause that matches all original column values.
    Returns (sql, params).
    Note: This can update multiple rows if the row isn't uniquely identifiable.
    """
    if not table or not columns or not isinstance(original_row, (list, tuple)):
        raise ValueError("Invalid inputs for build_update_sql")
    if target_col not in columns:
        raise ValueError("target_col not in columns")
    # Quote identifiers with backticks to avoid keyword clashes
    def q(name: str) -> str:
        return f"`{name}`"
    set_clause = f"{q(target_col)} = %s"
    params: list = [new_value]
    where_parts: list[str] = []
    for idx, col in enumerate(columns):
        val = original_row[idx] if idx < len(original_row) else None
        if val is None:
            where_parts.append(f"{q(col)} IS NULL")
        else:
            where_parts.append(f"{q(col)} = %s")
            params.append(val)
    where_sql = " AND ".join(where_parts) if where_parts else "1=1"
    sql = f"UPDATE {q(table)} SET {set_clause} WHERE {where_sql};"
    return sql, params


class DBTunnelGUI(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Country Game — DB Tunnel GUI")
        self.geometry("900x600")
        self.minsize(780, 520)

        # State
        self.conn: Optional[Any] = None
        self._busy = False
        self._log_q: "queue.Queue[str]" = queue.Queue()
        self.last_table: Optional[str] = None
        self.last_columns: list[str] = []
        self.allow_writes = tk.BooleanVar(value=False)

        self._build_ui()
        self._bind_events()
        self._log("Ready. Click Connect to open the SSH tunnel and DB connection.")

    # --- UI ---
    def _build_ui(self) -> None:
        root = ttk.Frame(self)
        root.pack(fill=tk.BOTH, expand=True)
        root.columnconfigure(0, weight=1)
        root.rowconfigure(1, weight=1)

        # Top bar
        bar = ttk.Frame(root)
        bar.grid(row=0, column=0, sticky="ew", pady=(8, 6), padx=8)

        self.btn_connect = ttk.Button(bar, text="Connect", command=self.on_connect)
        self.btn_connect.pack(side=tk.LEFT)
        self.btn_disconnect = ttk.Button(bar, text="Disconnect", command=self.on_disconnect, state=tk.DISABLED)
        self.btn_disconnect.pack(side=tk.LEFT, padx=(6, 0))
        self.btn_tables = ttk.Button(bar, text="List Tables", command=self.on_list_tables, state=tk.DISABLED)
        self.btn_tables.pack(side=tk.LEFT, padx=(6, 0))

        self.status_var = tk.StringVar(value="Status: Disconnected")
        status = ttk.Label(bar, textvariable=self.status_var)
        status.pack(side=tk.RIGHT)

        # Notebook with tabs
        self.notebook = ttk.Notebook(root)
        self.notebook.grid(row=1, column=0, sticky="nsew")

        # --- Browse tab ---
        self.tab_browse = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_browse, text="Browse")
        self.tab_browse.columnconfigure(1, weight=1)
        self.tab_browse.rowconfigure(0, weight=1)

        # Left: tables list
        left = ttk.Frame(self.tab_browse)
        left.grid(row=0, column=0, sticky="nsw", padx=(8, 4), pady=8)
        ttk.Label(left, text="Tables").pack(anchor="w")
        self.tv_tables = ttk.Treeview(left, columns=("name",), show="tree")
        self.tv_tables.pack(fill=tk.BOTH, expand=True)
        self.tv_tables.bind("<<TreeviewSelect>>", self._on_table_selected)
        self.tv_tables.bind("<Double-1>", self._on_table_double_click)

        # Right: rows preview
        right = ttk.Frame(self.tab_browse)
        right.grid(row=0, column=1, sticky="nsew", padx=(4, 8), pady=8)
        right.columnconfigure(0, weight=1)
        right.rowconfigure(1, weight=1)
        ttk.Label(right, text="Preview (first 100 rows)").grid(row=0, column=0, sticky="w")
        self.tv_rows = ttk.Treeview(right, columns=(), show="headings")
        self.tv_rows.grid(row=1, column=0, sticky="nsew")
        # Add a small scrollbar
        yscroll = ttk.Scrollbar(right, orient=tk.VERTICAL, command=self.tv_rows.yview)
        self.tv_rows.configure(yscrollcommand=yscroll.set)
        yscroll.grid(row=1, column=1, sticky="ns")

        # Simple editor controls for updating a single cell
        editor = ttk.Frame(right)
        editor.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        editor.columnconfigure(3, weight=1)
        ttk.Label(editor, text="Column:").grid(row=0, column=0, padx=(0, 6))
        self.cb_edit_col = ttk.Combobox(editor, state="readonly", values=[])
        self.cb_edit_col.grid(row=0, column=1, padx=(0, 10))
        ttk.Label(editor, text="New value:").grid(row=0, column=2, padx=(0, 6))
        self.e_edit_val = ttk.Entry(editor)
        self.e_edit_val.grid(row=0, column=3, sticky="ew")
        self.btn_update_cell = ttk.Button(editor, text="Update Selected Cell", command=self.on_update_cell, state=tk.DISABLED)
        self.btn_update_cell.grid(row=0, column=4, padx=(10, 0))

        # Enable update button when a row is selected
        self.tv_rows.bind("<<TreeviewSelect>>", lambda e: self._on_row_select())

        # --- Query tab ---
        self.tab_query = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_query, text="Query")
        self.tab_query.columnconfigure(1, weight=1)
        self.tab_query.rowconfigure(2, weight=1)

        ttk.Label(self.tab_query, text="SQL:").grid(row=0, column=0, sticky="w", padx=8, pady=(8, 6))
        self.query_var = tk.StringVar(value="SELECT DATABASE() AS db, NOW() AS now;")
        self.entry_query = ttk.Entry(self.tab_query, textvariable=self.query_var)
        self.entry_query.grid(row=0, column=1, sticky="ew", padx=(0, 8), pady=(8, 6))
        self.btn_run = ttk.Button(self.tab_query, text="Run", command=self.on_run_query, state=tk.DISABLED)
        self.btn_run.grid(row=0, column=2, padx=(0, 8), pady=(8, 6))
        self.cb_writes = ttk.Checkbutton(self.tab_query, text="Allow writes (INSERT/UPDATE/DELETE)", variable=self.allow_writes)
        self.cb_writes.grid(row=1, column=1, sticky="w", padx=(0, 8))

        # Query output
        self.query_txt = tk.Text(self.tab_query, height=18, wrap=tk.NONE)
        self.query_txt.grid(row=2, column=0, columnspan=3, sticky="nsew", padx=8, pady=(0, 8))
        self.query_txt.configure(state=tk.DISABLED)

        # --- Logs tab ---
        self.tab_logs = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_logs, text="Logs")
        self.tab_logs.columnconfigure(0, weight=1)
        self.tab_logs.rowconfigure(0, weight=1)
        self.txt = tk.Text(self.tab_logs, height=18, wrap=tk.NONE)
        self.txt.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        self.txt.configure(state=tk.DISABLED)

        # Poll log queue periodically
        self.after(100, self._drain_log)

    def _bind_events(self) -> None:
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # --- Helpers ---
    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        state = tk.DISABLED if busy else tk.NORMAL
        if self.conn is None:
            self.btn_connect.config(state=state)
            self.btn_disconnect.config(state=tk.DISABLED)
            self.btn_tables.config(state=tk.DISABLED)
            self.btn_run.config(state=tk.DISABLED)
        else:
            self.btn_connect.config(state=tk.DISABLED)
            self.btn_disconnect.config(state=state)
            self.btn_tables.config(state=state)
            self.btn_run.config(state=state)

    def _log(self, text: str) -> None:
        self._log_q.put(text)

    def _drain_log(self) -> None:
        flushed = False
        while True:
            try:
                line = self._log_q.get_nowait()
            except queue.Empty:
                break
            if not flushed:
                self.txt.configure(state=tk.NORMAL)
                flushed = True
            self.txt.insert(tk.END, line + "\n")
            self.txt.see(tk.END)
        if flushed:
            self.txt.configure(state=tk.DISABLED)
        self.after(120, self._drain_log)

    def _update_status(self, msg: str) -> None:
        self.status_var.set(f"Status: {msg}")

    # --- Actions ---
    def on_connect(self) -> None:
        if self.conn is not None:
            return
        self._set_busy(True)
        self._update_status("Connecting…")
        self._log("Connecting via SSH tunnel…")

        def worker():
            try:
                # Lazy import the tunnel helper to catch missing deps
                mod = importlib.import_module(
                    'projects.country_game.country_game_utilites.ssh_db_tunnel'
                )
                # Prefer connector-like function (returns (conn, closer))
                try:
                    conn, closer = mod.get_connector_connection_via_tunnel()  # type: ignore[attr-defined]
                except Exception:
                    conn = mod.connect_via_tunnel()  # type: ignore[attr-defined]
                    closer = None
                if conn is None:
                    raise RuntimeError("Tunnel or DB connection returned None.")
                # Quick sanity check
                cur = conn.cursor()
                cur.execute("SELECT DATABASE(), NOW();")
                row = cur.fetchone()
                try:
                    cur.close()
                except Exception:
                    pass
                # Store
                self.conn = conn
                self._log("Connected. Test query result: " + str(row))
                self._update_status("Connected")
            except ModuleNotFoundError as e:
                self._log(f"Import error: {e}")
                self._log("Hint: Ensure required packages are installed: \n"
                          "  pip install paramiko sshtunnel mysqlclient\n"
                          "If mysqlclient fails on Windows, try: pip install PyMySQL and update tunnel code.")
                self._update_status("Failed — missing dependencies")
            except Exception as e:
                self._log(f"Connection failed: {e}")
                # Special hint for Paramiko DSSKey issue
                if "DSSKey" in str(e):
                    self._log("Hint: Using Paramiko v3+. The tunnel helper includes a DSSKey compatibility shim.")
                self._update_status("Failed")
            finally:
                self._set_busy(False)
                self._refresh_buttons()

        threading.Thread(target=worker, daemon=True).start()

    def on_disconnect(self) -> None:
        if self.conn is None:
            return
        self._set_busy(True)
        self._update_status("Disconnecting…")

        def worker():
            try:
                try:
                    self.conn.close()
                except Exception:
                    pass
                self._log("Disconnected.")
                self._update_status("Disconnected")
            finally:
                self.conn = None
                self._set_busy(False)
                self._refresh_buttons()

        threading.Thread(target=worker, daemon=True).start()

    def on_list_tables(self) -> None:
        if self.conn is None:
            return
        self._set_busy(True)
        self._log("Listing tables…")

        def worker():
            try:
                cur = self.conn.cursor()
                cur.execute("SHOW TABLES;")
                rows = cur.fetchall() or []
                try:
                    cur.close()
                except Exception:
                    pass
                # Normalize to plain strings
                tables = []
                for r in rows:
                    if isinstance(r, (list, tuple)) and r:
                        val = r[0]
                    else:
                        val = r
                    if isinstance(val, bytes):
                        try:
                            val = val.decode('utf-8', errors='ignore')
                        except Exception:
                            val = str(val)
                    tables.append(str(val))
                if not tables:
                    self._log("No tables found or insufficient privileges.")
                else:
                    self._log("Tables:\n  - " + "\n  - ".join(tables))
                    # Populate Browse tab
                    self.after(0, lambda: self._set_tables(tables))
                    # Switch to Browse tab to emphasize navigation
                    try:
                        self.after(0, lambda: self.notebook.select(self.tab_browse))
                    except Exception:
                        pass
            except Exception as e:
                self._log(f"SHOW TABLES failed: {e}")
            finally:
                self._set_busy(False)
                self._refresh_buttons()

        threading.Thread(target=worker, daemon=True).start()

    def on_run_query(self) -> None:
        if self.conn is None:
            return
        sql = self.query_var.get().strip()
        if not sql:
            messagebox.showinfo("Empty", "Please enter a SELECT query.")
            return
        self._set_busy(True)
        self._log(f"Running query: {sql}")
        self._qprint(f">>> {sql}\n")

        def worker():
            try:
                cur = self.conn.cursor()
                lower = sql.strip().lower()
                if not lower.startswith("select") and not self.allow_writes.get():
                    self.after(0, lambda: self._qprint("Writes are disabled. Enable 'Allow writes' to execute.\n"))
                else:
                    cur.execute(sql)
                    if lower.startswith("select"):
                        rows = cur.fetchall() or []
                        if not rows:
                            self.after(0, lambda: self._qprint("(0 rows)\n\n"))
                        else:
                            for i, row in enumerate(rows, 1):
                                self.after(0, lambda r=row, i=i: self._qprint(f"[{i}] {r}\n"))
                            self.after(0, lambda: self._qprint("\n"))
                    else:
                        # Commit write operations
                        try:
                            self.conn.commit()
                        except Exception:
                            pass
                        rc = getattr(cur, "rowcount", None)
                        self.after(0, lambda rc=rc: self._qprint(f"OK, affected rows: {rc}\n"))
                        # Refresh current table preview if any
                        if self.last_table:
                            self.after(0, lambda: self.preview_table(self.last_table))
                try:
                    cur.close()
                except Exception:
                    pass
            except Exception as e:
                self._log(f"Query failed: {e}")
                self.after(0, lambda: self._qprint(f"Error: {e}\n"))
            finally:
                self._set_busy(False)
                self._refresh_buttons()

        threading.Thread(target=worker, daemon=True).start()

    # --- Browse helpers ---
    def _set_tables(self, tables: list[str]) -> None:
        try:
            self.tv_tables.delete(*self.tv_tables.get_children())
            for t in tables:
                self.tv_tables.insert("", tk.END, iid=t, text=t)
        except Exception:
            pass

    def _clear_rows_view(self) -> None:
        try:
            for c in self.tv_rows["columns"]:
                self.tv_rows.heading(c, text="")
                self.tv_rows.column(c, width=80)
            self.tv_rows["columns"] = ()
            self.tv_rows.delete(*self.tv_rows.get_children())
        except Exception:
            pass

    def _update_rows_view(self, columns: list[str], rows: list[tuple]) -> None:
        self._clear_rows_view()
        try:
            self.tv_rows["columns"] = columns
            for c in columns:
                self.tv_rows.heading(c, text=c)
                self.tv_rows.column(c, width=max(80, int(800 / max(1, len(columns)))))
            for r in rows:
                # Ensure tuple length matches columns
                try:
                    vals = list(r)
                    # decode bytes if any
                    for i, v in enumerate(vals):
                        if isinstance(v, (bytes, bytearray)):
                            try:
                                vals[i] = v.decode("utf-8", errors="ignore")
                            except Exception:
                                vals[i] = str(v)
                    self.tv_rows.insert("", tk.END, values=vals)
                except Exception:
                    continue
        except Exception:
            pass

    def _on_table_selected(self, event=None) -> None:
        try:
            sel = self.tv_tables.selection()
            if not sel:
                return
            table = sel[0]
        except Exception:
            return
        self.preview_table(table)

    def preview_table(self, table: str) -> None:
        if self.conn is None:
            return
        self._set_busy(True)
        self._log(f"Previewing first 100 rows from `{table}`…")

        def worker():
            try:
                cur = self.conn.cursor()
                # Use backticks to avoid keyword clashes; no user input other than table name from SHOW TABLES.
                sql = f"SELECT * FROM `{table}` LIMIT 100;"
                cur.execute(sql)
                rows = cur.fetchall() or []
                # Extract column names
                cols = []
                try:
                    cols = [d[0] for d in (cur.description or [])]
                except Exception:
                    cols = []
                try:
                    cur.close()
                except Exception:
                    pass
                # Update UI on main thread
                self.after(0, lambda: self._update_rows_view(cols, rows))
                # Also switch to Browse tab (already there) and write a note in Query tab output
                self.after(0, lambda: self._qprint(f"-- Previewed {len(rows)} row(s) from {table}\n"))
            except Exception as e:
                self._log(f"Preview failed for {table}: {e}")
            finally:
                self._set_busy(False)
                self._refresh_buttons()

    # --- Query output helper ---
    def _qprint(self, text: str) -> None:
        try:
            self.query_txt.configure(state=tk.NORMAL)
            self.query_txt.insert(tk.END, text)
            self.query_txt.see(tk.END)
            self.query_txt.configure(state=tk.DISABLED)
        except Exception:
            pass

    def _refresh_buttons(self) -> None:
        if self.conn is None:
            self.btn_connect.config(state=tk.NORMAL if not self._busy else tk.DISABLED)
            self.btn_disconnect.config(state=tk.DISABLED)
            self.btn_tables.config(state=tk.DISABLED)
            self.btn_run.config(state=tk.DISABLED)
        else:
            self.btn_connect.config(state=tk.DISABLED)
            st = tk.NORMAL if not self._busy else tk.DISABLED
            for b in (self.btn_disconnect, self.btn_tables, self.btn_run):
                b.config(state=st)

    def _on_close(self) -> None:
        # Try to disconnect cleanly to stop the tunnel background threads
        try:
            if self.conn is not None:
                try:
                    self.conn.close()
                except Exception:
                    pass
        finally:
            self.destroy()


def main() -> int:
    app = DBTunnelGUI()
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
