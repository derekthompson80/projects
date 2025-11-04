from __future__ import annotations

import os
import json
import time
import random
from typing import Any, Dict, List, Optional
from datetime import datetime

# Best-effort load environment from a local .env file in development
try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except Exception:
    pass

# Base paths for optional file fallback
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
COMMENTS_DIR = os.path.join(BASE_DIR, 'blog_comments')


def _ensure_comments_dir() -> None:
    try:
        os.makedirs(COMMENTS_DIR, exist_ok=True)
    except Exception:
        pass


def _comments_path(entry_id: str) -> str:
    return os.path.join(COMMENTS_DIR, f"{entry_id}.json")

# Optional deps, imported lazily inside connect helpers
# - MySQLdb
# - sshtunnel
# - paramiko (for DSSKey workaround)

# Retry config (tunable via env)
_DEF_MAX_TRIES = int(os.environ.get('BLOG_DB_MAX_RETRIES', '5'))
_DEF_BASE_DELAY = float(os.environ.get('BLOG_DB_BASE_DELAY', '0.25'))
_DEF_BACKOFF = float(os.environ.get('BLOG_DB_BACKOFF', '2.0'))
_DEF_CAP_DELAY = float(os.environ.get('BLOG_DB_CAP_DELAY', '3.0'))


def _with_retries(fn, *, max_tries: Optional[int] = None,
                  base_delay: Optional[float] = None,
                  backoff: Optional[float] = None,
                  cap_delay: Optional[float] = None):
    tries = max_tries or _DEF_MAX_TRIES
    base = base_delay or _DEF_BASE_DELAY
    factor = backoff or _DEF_BACKOFF
    cap = cap_delay or _DEF_CAP_DELAY
    last_exc: Exception | None = None
    for attempt in range(1, tries + 1):
        try:
            return fn()
        except Exception as e:  # noqa: BLE001
            last_exc = e
            if attempt >= tries:
                raise
            delay = min(cap, base * (factor ** (attempt - 1)))
            jitter = random.uniform(0, delay * 0.2)
            time.sleep(delay + jitter)
    if last_exc:
        raise last_exc


# --- Dev/file fallback helpers ---

def _db_configured() -> bool:
    """Return True if minimum MySQL configuration env vars appear to be set.
    Works for direct connect and SSH tunnel modes.
    """
    db_user = os.environ.get('PA_DB_USER') or os.environ.get('MYSQL_USER')
    db_pass = os.environ.get('PA_DB_PASS') or os.environ.get('MYSQL_PASSWORD')
    db_name = os.environ.get('PA_DB_NAME') or os.environ.get('MYSQL_DATABASE') or 'spade605$blog'
    # Host can be provided via PA_DB_HOST/MYSQL_HOST or via SSH tunnel remote host
    db_host = os.environ.get('PA_DB_HOST') or os.environ.get('MYSQL_HOST') or os.environ.get('PA_DB_HOST')
    # Require at least user, pass, name. Host may be implied in some PA setups, but usually present.
    return bool(db_user and db_pass and db_name and db_host)


def _dev_mode_enabled() -> bool:
    return (
        os.environ.get('BLOG_DEBUG', '').lower() in ('1', 'true', 'yes') or
        os.environ.get('FLASK_ENV', '').lower() == 'development'
    )


def _use_file_fallback() -> bool:
    """Decide whether to use local file-backed fallback.
    If DB is not configured, default to fallback unless explicitly disabled
    via BLOG_DEV_FALLBACK in ('0','false','no'). If DB is configured, do not fallback.
    """
    if _db_configured():
        return False
    flag = os.environ.get('BLOG_DEV_FALLBACK')
    if flag is None:
        # No explicit flag; default to fallback when DB missing
        return True
    return flag.lower() in ('1', 'true', 'yes', 'on', 'enable', 'enabled')


# --- MySQL connection helpers (direct or via SSH tunnel) ---

def _mysql_connect():
    try:
        import MySQLdb  # type: ignore
    except Exception as e:
        raise RuntimeError('MySQLdb dependency is not installed') from e

    db_host = os.environ.get('PA_DB_HOST') or os.environ.get('MYSQL_HOST')
    db_user = os.environ.get('PA_DB_USER') or os.environ.get('MYSQL_USER')
    db_pass = os.environ.get('PA_DB_PASS') or os.environ.get('MYSQL_PASSWORD')
    db_name = os.environ.get('PA_DB_NAME') or os.environ.get('MYSQL_DATABASE') or 'spade605$blog'
    db_port = int(os.environ.get('PA_DB_PORT') or os.environ.get('MYSQL_PORT') or '3306')

    ssh_host = os.environ.get('PA_SSH_HOST')
    if not ssh_host:
        if not (db_host and db_user and db_pass and db_name):
            raise RuntimeError('Database configuration missing; set PA_DB_* or MYSQL_* env vars')
        return MySQLdb.connect(
            user=db_user,
            passwd=db_pass,
            host=db_host,
            port=db_port,
            db=db_name,
            connect_timeout=10,
            charset='utf8mb4',
            use_unicode=True,
        )

    # SSH tunnel mode
    try:
        import sshtunnel  # type: ignore
        import paramiko  # type: ignore
    except Exception as e:
        raise RuntimeError('sshtunnel/paramiko dependencies are not installed') from e

    # Paramiko DSSKey workaround (for older sshtunnel expectations)
    if not hasattr(paramiko, 'DSSKey'):
        try:
            paramiko.DSSKey = paramiko.RSAKey  # type: ignore[attr-defined]
        except Exception:
            pass

    sshtunnel.SSH_TIMEOUT = 10.0
    sshtunnel.TUNNEL_TIMEOUT = 10.0

    ssh_user = os.environ.get('PA_SSH_USER')
    ssh_pass = os.environ.get('PA_SSH_PASS')
    ssh_key = os.environ.get('PA_SSH_KEY')

    remote_host = db_host or os.environ.get('PA_DB_HOST')
    remote_port = db_port

    tunnel = sshtunnel.SSHTunnelForwarder(
        (ssh_host),
        ssh_username=ssh_user,
        ssh_password=ssh_pass if ssh_key is None else None,
        ssh_pkey=ssh_key,
        remote_bind_address=(remote_host, remote_port),
        allow_agent=False,
        host_pkey_directories=[],
        set_keepalive=15,
    )
    tunnel.start()

    conn = MySQLdb.connect(
        user=db_user,
        passwd=db_pass,
        host='127.0.0.1',
        port=tunnel.local_bind_port,
        db=db_name,
        connect_timeout=10,
        charset='utf8mb4',
        use_unicode=True,
    )
    setattr(conn, '_ssh_tunnel', tunnel)
    return conn


def _mysql_close(conn) -> None:
    if conn is None:
        return
    try:
        conn.close()
    except Exception:
        pass
    tunnel = getattr(conn, '_ssh_tunnel', None)
    if tunnel is not None:
        try:
            tunnel.stop()
        except Exception:
            pass


# --- Schema management ---

def init_schema() -> None:
    """Ensure required tables exist: entries, blog_comments.
    In dev fallback mode, delegate to the file-backed adapter from blog_db.py.
    """
    if _use_file_fallback():
        # Lazy import to avoid circulars if any
        import blog_db as _fb  # type: ignore
        return _fb.init_schema()

    def _impl():
        conn = _mysql_connect()
        try:
            cur = conn.cursor()
            # entries table
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS entries (
                    id VARCHAR(255) PRIMARY KEY,
                    title VARCHAR(512) NOT NULL,
                    author VARCHAR(255) NOT NULL,
                    date VARCHAR(32) NOT NULL,
                    content MEDIUMTEXT NOT NULL,
                    media_json MEDIUMTEXT NULL
                ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
                """
            )
            # comments table (with FK cascade)
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS blog_comments (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    entry_id VARCHAR(255) NOT NULL,
                    author VARCHAR(255) NOT NULL,
                    date VARCHAR(32) NOT NULL,
                    content MEDIUMTEXT NOT NULL,
                    INDEX idx_entry_date (entry_id, date),
                    CONSTRAINT fk_comments_entry
                        FOREIGN KEY (entry_id) REFERENCES entries(id)
                        ON DELETE CASCADE
                ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
                """
            )
            conn.commit()
        finally:
            _mysql_close(conn)
    return _with_retries(_impl)


# --- Entries CRUD ---

def _parse_media(media: Any) -> Optional[Dict[str, Any]]:
    if isinstance(media, dict):
        return media
    if isinstance(media, str):
        try:
            obj = json.loads(media)
            return obj if isinstance(obj, dict) else None
        except Exception:
            return None
    return None


def insert_entry(title: str, content: str, author: str, media: Optional[Dict[str, Any]] = None) -> str:
    if _use_file_fallback():
        # Delegate to file-backed adapter
        try:
            from . import blog_db as _fb  # type: ignore
        except ImportError:
            import projects.Blog.blog_db as _fb  # type: ignore
        return _fb.insert_entry(title, content, author, media)

    def _impl():
        conn = _mysql_connect()
        try:
            cur = conn.cursor()
            # Generate id similar to prior approach: timestamp + safe title
            ts = datetime.now().strftime('%Y%m%d_%H%M%S')
            safe_title = ''.join(c if c.isalnum() else '_' for c in (title or ''))
            entry_id = f"{ts}_{safe_title}" if safe_title else ts
            media_json = json.dumps(media, ensure_ascii=False) if isinstance(media, dict) else None
            cur.execute(
                "INSERT INTO entries (id, title, author, date, content, media_json) VALUES (%s,%s,%s,%s,%s,%s)",
                (
                    entry_id,
                    title or 'Untitled',
                    author or 'Anonymous',
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    content or '',
                    media_json,
                ),
            )
            conn.commit()
            return entry_id
        finally:
            _mysql_close(conn)
    return _with_retries(_impl)


def get_entries() -> List[Dict[str, Any]]:
    if _use_file_fallback():
        try:
            from . import blog_db as _fb  # type: ignore
        except ImportError:
            import projects.Blog.blog_db as _fb  # type: ignore
        return _fb.get_entries()

    def _impl():
        conn = _mysql_connect()
        try:
            cur = conn.cursor()
            cur.execute("SELECT id, title, author, date, content, media_json FROM entries")
            rows = cur.fetchall()
            items: List[Dict[str, Any]] = []
            for r in rows:
                entry_id, title, author, date_str, content, media_json = r
                items.append({
                    'id': entry_id,
                    'title': title or 'Untitled',
                    'author': author or 'Anonymous',
                    'date': date_str or '',
                    'content': content or '',
                    'media': _parse_media(media_json),
                })
            # Sort by date desc (string parse fallback)
            def parse_dt(s: str) -> datetime:
                for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y%m%d_%H%M%S"):
                    try:
                        return datetime.strptime(s, fmt)
                    except Exception:
                        continue
                return datetime.min
            items.sort(key=lambda e: parse_dt(e.get('date', '')), reverse=True)
            return items
        finally:
            _mysql_close(conn)
    return _with_retries(_impl)


def get_entry(entry_id: str) -> Optional[Dict[str, Any]]:
    if _use_file_fallback():
        try:
            from . import blog_db as _fb  # type: ignore
        except ImportError:
            import projects.Blog.blog_db as _fb  # type: ignore
        return _fb.get_entry(entry_id)

    def _impl():
        conn = _mysql_connect()
        try:
            cur = conn.cursor()
            cur.execute("SELECT id, title, author, date, content, media_json FROM entries WHERE id=%s", (entry_id,))
            row = cur.fetchone()
            if not row:
                return None
            entry_id2, title, author, date_str, content, media_json = row
            return {
                'id': entry_id2,
                'title': title or 'Untitled',
                'author': author or 'Anonymous',
                'date': date_str or '',
                'content': content or '',
                'media': _parse_media(media_json),
            }
        finally:
            _mysql_close(conn)
    return _with_retries(_impl)


def update_entry(entry_id: str, title: str, content: str, author: str, media: Optional[Dict[str, Any]] = None) -> bool:
    if _use_file_fallback():
        try:
            from . import blog_db as _fb  # type: ignore
        except ImportError:
            import projects.Blog.blog_db as _fb  # type: ignore
        return _fb.update_entry(entry_id, title, content, author, media)

    def _impl():
        conn = _mysql_connect()
        try:
            cur = conn.cursor()
            # Preserve original date
            cur.execute("SELECT date FROM entries WHERE id=%s", (entry_id,))
            row = cur.fetchone()
            if not row:
                return False
            date_str = row[0] or datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            media_json = json.dumps(media, ensure_ascii=False) if isinstance(media, dict) else None
            cur.execute(
                "UPDATE entries SET title=%s, author=%s, date=%s, content=%s, media_json=%s WHERE id=%s",
                (
                    title or 'Untitled',
                    author or 'Anonymous',
                    date_str,
                    content or '',
                    media_json,
                    entry_id,
                ),
            )
            conn.commit()
            return cur.rowcount > 0
        finally:
            _mysql_close(conn)
    return _with_retries(_impl)


def delete_entry(entry_id: str) -> bool:
    if _use_file_fallback():
        try:
            from . import blog_db as _fb  # type: ignore
        except ImportError:
            import projects.Blog.blog_db as _fb  # type: ignore
        return _fb.delete_entry(entry_id)

    def _impl():
        conn = _mysql_connect()
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM entries WHERE id=%s", (entry_id,))
            conn.commit()
            return cur.rowcount > 0
        finally:
            _mysql_close(conn)
    return _with_retries(_impl)


# --- Comments API ---

def get_comments(entry_id: str) -> List[Dict[str, Any]]:
    if _use_file_fallback():
        _ensure_comments_dir()
        path = _comments_path(entry_id)
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if isinstance(data, list):
                # Normalize items
                out: List[Dict[str, Any]] = []
                for it in data:
                    if isinstance(it, dict):
                        out.append({
                            'id': int(it.get('id') or 0),
                            'author': it.get('author') or 'Anonymous',
                            'date': it.get('date') or '',
                            'content': it.get('content') or '',
                        })
                return out
        except Exception:
            return []
        return []

    def _impl():
        conn = _mysql_connect()
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT id, author, date, content FROM blog_comments WHERE entry_id=%s ORDER BY date ASC, id ASC",
                (entry_id,),
            )
            rows = cur.fetchall()
            results: List[Dict[str, Any]] = []
            for cid, author, date_str, content in rows:
                results.append({
                    'id': int(cid),
                    'author': author or 'Anonymous',
                    'date': date_str or '',
                    'content': content or '',
                })
            return results
        finally:
            _mysql_close(conn)
    return _with_retries(_impl)


def comments_count(entry_id: str) -> int:
    """Return number of comments for an entry.
    - In file-fallback mode: prefer blog_db.comments_count if available; otherwise
      count items in blog_comments/<entry_id>.json directly.
    - In MySQL mode: query COUNT(*) from blog_comments.
    """
    if _use_file_fallback():
        # Try multiple import strategies for blog_db, tolerate older versions
        _fb = None
        try:
            from . import blog_db as _fb  # type: ignore
        except Exception:
            try:
                import projects.Blog.blog_db as _fb  # type: ignore
            except Exception:
                try:
                    import blog_db as _fb  # type: ignore
                except Exception:
                    _fb = None
        if _fb is not None:
            try:
                # Use blog_db's own implementation when present
                return int(_fb.comments_count(entry_id))  # type: ignore[attr-defined]
            except AttributeError:
                # Older blog_db without comments_count; fall through to file count
                pass
            except Exception:
                # Any unexpected failure: fall through to file count
                pass
        # Direct file count fallback
        try:
            _ensure_comments_dir()
            path = _comments_path(entry_id)
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if isinstance(data, list):
                    return len(data)
        except Exception:
            return 0
        return 0

    def _impl():
        conn = _mysql_connect()
        try:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM blog_comments WHERE entry_id=%s", (entry_id,))
            row = cur.fetchone()
            return int(row[0]) if row and row[0] is not None else 0
        finally:
            _mysql_close(conn)
    return _with_retries(_impl)


def add_comment(entry_id: str, author: str, content: str, date_str: Optional[str] = None) -> int:
    if _use_file_fallback():
        # File-backed comments: stored as a list of dicts in blog_comments/<entry_id>.json
        _ensure_comments_dir()
        path = _comments_path(entry_id)
        items: List[Dict[str, Any]] = []
        try:
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        items = data
        except Exception:
            items = []
        new_id = (items[-1].get('id') + 1) if items and isinstance(items[-1].get('id'), int) else len(items) + 1
        ds = date_str or datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        items.append({
            'id': new_id,
            'author': author or 'Anonymous',
            'date': ds,
            'content': content or '',
        })
        try:
            tmp = path + '.tmp'
            with open(tmp, 'w', encoding='utf-8') as f:
                json.dump(items, f, indent=2, ensure_ascii=False)
            os.replace(tmp, path)
        except Exception:
            pass
        return int(new_id)

    def _impl():
        conn = _mysql_connect()
        try:
            cur = conn.cursor()
            ds = date_str or datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cur.execute(
                "INSERT INTO blog_comments (entry_id, author, date, content) VALUES (%s,%s,%s,%s)",
                (entry_id, author or 'Anonymous', ds, content or ''),
            )
            conn.commit()
            cur.execute("SELECT LAST_INSERT_ID()")
            row = cur.fetchone()
            return int(row[0]) if row and row[0] is not None else 0
        finally:
            _mysql_close(conn)
    return _with_retries(_impl)


# --- Health check ---

def health_check() -> bool:
    if _use_file_fallback():
        # File fallback is considered healthy for local development
        return True
    # If DB not configured and fallback disabled, signal unconfigured by raising
    if not _db_configured():
        raise RuntimeError('Database configuration missing; set PA_DB_* or MYSQL_* env vars')

    def _impl():
        conn = _mysql_connect()
        try:
            cur = conn.cursor()
            cur.execute("SELECT 1")
            _ = cur.fetchone()
            return True
        finally:
            _mysql_close(conn)
    return bool(_with_retries(_impl))