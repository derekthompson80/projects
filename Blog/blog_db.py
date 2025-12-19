import os
from pathlib import Path
from typing import Optional, Dict, Any, List
import datetime
import atexit

try:
    from dotenv import load_dotenv
except Exception:
    load_dotenv = None

import MySQLdb
from sshtunnel import SSHTunnelForwarder

# --------------------------------------------------
# Load .env
# --------------------------------------------------
if load_dotenv:
    load_dotenv(dotenv_path=Path(__file__).with_name(".env"))

# --------------------------------------------------
# SSH Config
# --------------------------------------------------
SSH_HOST = os.getenv("SSH_HOST")
SSH_PORT = int(os.getenv("SSH_PORT", "22"))
SSH_USER = os.getenv("SSH_USER")
SSH_KEY_PATH = os.getenv("SSH_KEY_PATH")
SSH_PASSWORD = os.getenv("SSH_PASSWORD")

# --------------------------------------------------
# MySQL Config (local to SSH server)
# --------------------------------------------------
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")

# --------------------------------------------------
# Global SSH tunnel
# --------------------------------------------------
_tunnel: Optional[SSHTunnelForwarder] = None

def get_ssh_tunnel() -> SSHTunnelForwarder:
    """Return a running SSH tunnel, start it if not already running."""
    global _tunnel
    if _tunnel is None or not _tunnel.is_active:
        if not SSH_HOST or not SSH_USER:
            raise RuntimeError("SSH_HOST and SSH_USER must be set")

        tunnel_kwargs = {
            "ssh_address_or_host": (SSH_HOST, SSH_PORT),
            "ssh_username": SSH_USER,
            "remote_bind_address": (DB_HOST, DB_PORT),
        }

        if SSH_KEY_PATH:
            tunnel_kwargs["ssh_pkey"] = SSH_KEY_PATH
        elif SSH_PASSWORD:
            tunnel_kwargs["ssh_password"] = SSH_PASSWORD
        else:
            raise RuntimeError("Provide SSH_KEY_PATH or SSH_PASSWORD")

        _tunnel = SSHTunnelForwarder(**tunnel_kwargs)
        _tunnel.start()

        # Ensure tunnel stops when script exits
        atexit.register(lambda: _tunnel.stop())
    return _tunnel

# --------------------------------------------------
# Database helpers
# --------------------------------------------------
def _ensure_database_exists():
    tunnel = get_ssh_tunnel()
    conn = MySQLdb.connect(
        host="127.0.0.1",
        port=tunnel.local_bind_port,
        user=DB_USER,
        passwd=DB_PASSWORD,
        connect_timeout=10,
        charset="utf8mb4",
        use_unicode=True,
    )
    try:
        cur = conn.cursor()
        cur.execute(
            f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
        )
        conn.commit()
    finally:
        conn.close()

def open_connection():
    tunnel = get_ssh_tunnel()
    _ensure_database_exists()
    conn = MySQLdb.connect(
        host="127.0.0.1",
        port=tunnel.local_bind_port,
        user=DB_USER,
        passwd=DB_PASSWORD,
        db=DB_NAME,
        connect_timeout=10,
        charset="utf8mb4",
        use_unicode=True,
    )
    return conn

def _close(conn):
    try:
        conn.close()
    except Exception:
        pass

# --------------------------------------------------
# Schema
# --------------------------------------------------
def init_schema() -> None:
    conn = open_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS entries (
                id INT AUTO_INCREMENT PRIMARY KEY,
                entry_key VARCHAR(64) UNIQUE,
                title VARCHAR(255) NOT NULL,
                author VARCHAR(128) NOT NULL,
                created_at DATETIME NOT NULL,
                content LONGTEXT NOT NULL,
                media_id VARCHAR(64) NULL,
                media_type VARCHAR(16) NULL,
                media_url TEXT NULL,
                media_thumbnail TEXT NULL,
                media_width VARCHAR(16) NULL,
                media_height VARCHAR(16) NULL,
                media_attribution TEXT NULL
            ) CHARACTER SET utf8mb4;
            """
        )
        conn.commit()
    finally:
        _close(conn)

# --------------------------------------------------
# CRUD Operations
# --------------------------------------------------
def insert_entry(title: str, content: str, author: str, media: Optional[Dict[str, Any]] = None) -> str:
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_title = "".join(c if c.isalnum() else "_" for c in title)
    entry_key = f"{timestamp}_{safe_title}"

    conn = open_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO entries
            (entry_key, title, author, created_at, content,
             media_id, media_type, media_url, media_thumbnail,
             media_width, media_height, media_attribution)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                entry_key,
                title,
                author,
                datetime.datetime.now(),
                content,
                (media or {}).get("id"),
                (media or {}).get("type"),
                (media or {}).get("url"),
                (media or {}).get("thumbnail"),
                (media or {}).get("width"),
                (media or {}).get("height"),
                (media or {}).get("attribution"),
            ),
        )
        conn.commit()
        return entry_key
    finally:
        _close(conn)

def get_entries() -> List[Dict[str, Any]]:
    conn = open_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT entry_key, title, author, created_at, content,
                   media_id, media_type, media_url, media_thumbnail,
                   media_width, media_height, media_attribution
            FROM entries
            ORDER BY created_at DESC
            """
        )
        rows = cur.fetchall()
        entries = []
        for r in rows:
            media = None
            if r[5]:
                media = {
                    "id": r[5], "type": r[6] or "", "url": r[7] or "",
                    "thumbnail": r[8] or "", "width": r[9] or "",
                    "height": r[10] or "", "attribution": r[11] or ""
                }
            entries.append({
                "id": r[0],
                "title": r[1],
                "author": r[2],
                "date": r[3].strftime("%Y-%m-%d %H:%M:%S"),
                "content": r[4],
                "media": media
            })
        return entries
    finally:
        _close(conn)

def get_entry(entry_id: str) -> Optional[Dict[str, Any]]:
    conn = open_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT entry_key, title, author, created_at, content,
                   media_id, media_type, media_url, media_thumbnail,
                   media_width, media_height, media_attribution
            FROM entries
            WHERE entry_key=%s
            """, (entry_id,)
        )
        r = cur.fetchone()
        if not r:
            return None
        media = None
        if r[5]:
            media = {
                "id": r[5], "type": r[6] or "", "url": r[7] or "",
                "thumbnail": r[8] or "", "width": r[9] or "",
                "height": r[10] or "", "attribution": r[11] or ""
            }
        return {
            "id": r[0],
            "title": r[1],
            "author": r[2],
            "date": r[3].strftime("%Y-%m-%d %H:%M:%S"),
            "content": r[4],
            "media": media
        }
    finally:
        _close(conn)

def update_entry(entry_id: str, title: str, content: str, author: str, media: Optional[Dict[str, Any]] = None) -> bool:
    conn = open_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE entries
            SET title=%s, author=%s, content=%s,
                media_id=%s, media_type=%s, media_url=%s,
                media_thumbnail=%s, media_width=%s,
                media_height=%s, media_attribution=%s
            WHERE entry_key=%s
            """,
            (
                title, author, content,
                (media or {}).get("id"),
                (media or {}).get("type"),
                (media or {}).get("url"),
                (media or {}).get("thumbnail"),
                (media or {}).get("width"),
                (media or {}).get("height"),
                (media or {}).get("attribution"),
                entry_id
            ),
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        _close(conn)

def delete_entry(entry_id: str) -> bool:
    conn = open_connection()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM entries WHERE entry_key=%s", (entry_id,))
        conn.commit()
        return cur.rowcount > 0
    finally:
        _close(conn)
