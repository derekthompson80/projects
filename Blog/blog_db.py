import os
from pathlib import Path
try:
    from dotenv import load_dotenv  # type: ignore
except Exception:
    load_dotenv = None  # type: ignore
import MySQLdb
from typing import Optional, Dict, Any, List

# Load environment variables from .env located alongside this file
if load_dotenv:
    load_dotenv(dotenv_path=Path(__file__).with_name('.env'))

# Direct MySQL connection settings from environment; avoid hardcoded secrets
DB_HOST = os.getenv('DB_HOST', '127.0.0.1')
DB_PORT = int(os.getenv('DB_PORT', '3305'))
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_NAME = os.getenv('DB_NAME')

# Note: We intentionally do not validate DB settings at import time to avoid
# raising errors when the database feature is not used. Validation happens in
# the connection function below.

def _ensure_database_exists() -> None:
    """Ensure the target database exists with utf8mb4 settings before connecting to it.
    Connects without selecting a DB, creates it if missing, then returns.
    """
    if not DB_NAME:
        raise RuntimeError("DB_NAME is not set. Define it in environment or .env.")
    # Connect to server without selecting DB
    server_conn = MySQLdb.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", "3305")),
        user=os.getenv("DB_USER"),
        passwd=os.getenv("DB_PASSWORD"),
        connect_timeout=10,
        charset="utf8mb4",
        use_unicode=True,
    )
    try:
        cur = server_conn.cursor()
        cur.execute(
            f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
        )
        server_conn.commit()
    finally:
        try:
            server_conn.close()
        except Exception:
            pass


def open_connection():
    _ensure_database_exists()
    conn = MySQLdb.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER"),
        passwd=os.getenv("DB_PASSWORD"),
        db=os.getenv("DB_NAME"),
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


def insert_entry(title: str, content: str, author: str, media: Optional[Dict[str, Any]] = None) -> str:
    import datetime
    # Create entry_key to keep compatibility with file-based id (timestamp based)
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
             media_id, media_type, media_url, media_thumbnail, media_width, media_height, media_attribution)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                entry_key,
                title,
                author,
                datetime.datetime.now(),
                content,
                (media or {}).get('id'),
                (media or {}).get('type'),
                (media or {}).get('url'),
                (media or {}).get('thumbnail'),
                (media or {}).get('width'),
                (media or {}).get('height'),
                (media or {}).get('attribution'),
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
        cur.execute("SELECT entry_key, title, author, created_at, content, media_id, media_type, media_url, media_thumbnail, media_width, media_height, media_attribution FROM entries ORDER BY created_at DESC")
        rows = cur.fetchall()
        entries: List[Dict[str, Any]] = []
        for r in rows:
            media = None
            if r[5]:
                media = {
                    'id': r[5],
                    'type': r[6] or '',
                    'url': r[7] or '',
                    'thumbnail': r[8] or '',
                    'width': r[9] or '',
                    'height': r[10] or '',
                    'attribution': r[11] or '',
                }
            # Truncate content preview like file-based approach will be done in route
            entries.append({
                'id': r[0],
                'title': r[1],
                'author': r[2],
                'date': r[3].strftime('%Y-%m-%d %H:%M:%S') if r[3] else '',
                'content': r[4],
                'media': media,
            })
        return entries
    finally:
        _close(conn)


def get_entry(entry_id: str) -> Optional[Dict[str, Any]]:
    conn = open_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT entry_key, title, author, created_at, content, media_id, media_type, media_url, media_thumbnail, media_width, media_height, media_attribution FROM entries WHERE entry_key=%s",
            (entry_id,)
        )
        r = cur.fetchone()
        if not r:
            return None
        media = None
        if r[5]:
            media = {
                'id': r[5],
                'type': r[6] or '',
                'url': r[7] or '',
                'thumbnail': r[8] or '',
                'width': r[9] or '',
                'height': r[10] or '',
                'attribution': r[11] or '',
            }
        return {
            'id': r[0],
            'title': r[1],
            'author': r[2],
            'date': r[3].strftime('%Y-%m-%d %H:%M:%S') if r[3] else '',
            'content': r[4],
            'media': media,
        }
    finally:
        _close(conn)


def update_entry(entry_id: str, title: str, content: str, author: str, media: Optional[Dict[str, Any]] = None) -> bool:
    """Update an existing entry by entry_key. Preserves created_at."""
    conn = open_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE entries
            SET title=%s, author=%s, content=%s,
                media_id=%s, media_type=%s, media_url=%s, media_thumbnail=%s, media_width=%s, media_height=%s, media_attribution=%s
            WHERE entry_key=%s
            """,
            (
                title,
                author,
                content,
                (media or {}).get('id'),
                (media or {}).get('type'),
                (media or {}).get('url'),
                (media or {}).get('thumbnail'),
                (media or {}).get('width'),
                (media or {}).get('height'),
                (media or {}).get('attribution'),
                entry_id,
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