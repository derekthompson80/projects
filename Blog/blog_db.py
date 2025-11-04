from __future__ import annotations

"""
File-based backend for Blog to remove Paramiko/MySQL dependencies.

This module provides the same public API as the previous DB-backed version but
stores data in JSON files under the Blog directory. This eliminates
any need for paramiko/sshtunnel/MySQL drivers.
"""

from typing import Optional, Dict, Any, List
import os
import json
from datetime import datetime, timedelta
import secrets
import time
import random

# --- Retry and backend selection helpers ---

_DEF_MAX_TRIES = int(os.environ.get('BLOG_DB_MAX_RETRIES', '5'))
_DEF_BASE_DELAY = float(os.environ.get('BLOG_DB_BASE_DELAY', '0.25'))
_DEF_BACKOFF = float(os.environ.get('BLOG_DB_BACKOFF', '2.0'))
_DEF_CAP_DELAY = float(os.environ.get('BLOG_DB_CAP_DELAY', '3.0'))


def _is_transient(exc: Exception) -> bool:
    # Treat most IO/OS and generic exceptions as transient by default
    transient_types = (OSError, IOError, TimeoutError)
    if isinstance(exc, transient_types):
        return True
    # MySQLdb OperationalError often means transient issues
    try:
        import MySQLdb  # type: ignore
        if isinstance(exc, MySQLdb.OperationalError):
            return True
    except Exception:
        pass
    return True  # default to retry unless explicitly validated elsewhere


def _with_retries(fn, *, max_tries: int | None = None, base_delay: float | None = None,
                  backoff: float | None = None, cap_delay: float | None = None):
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
            if not _is_transient(e) or attempt >= tries:
                raise
            # Exponential backoff with jitter
            delay = min(cap, base * (factor ** (attempt - 1)))
            jitter = random.uniform(0, delay * 0.2)
            time.sleep(delay + jitter)
    if last_exc:
        raise last_exc


def _use_mysql() -> bool:
    return os.environ.get('BLOG_DB_BACKEND', '').lower() == 'mysql'


# --- MySQL adapter (optional, env-driven) ---

def _mysql_connect():
    try:
        import MySQLdb  # type: ignore
    except Exception as e:
        raise RuntimeError('Database dependencies are not installed: MySQLdb') from e

    # Direct DB connection parameters
    db_host = os.environ.get('PA_DB_HOST') or os.environ.get('MYSQL_HOST')
    db_user = os.environ.get('PA_DB_USER') or os.environ.get('MYSQL_USER')
    db_pass = os.environ.get('PA_DB_PASS') or os.environ.get('MYSQL_PASSWORD')
    db_name = os.environ.get('PA_DB_NAME') or os.environ.get('MYSQL_DATABASE')
    db_port = int(os.environ.get('PA_DB_PORT') or os.environ.get('MYSQL_PORT') or '3306')

    # Optional SSH tunnel for PythonAnywhere
    ssh_host = os.environ.get('PA_SSH_HOST')
    if ssh_host:
        try:
            import sshtunnel  # type: ignore
            import paramiko  # type: ignore
        except Exception as e:
            raise RuntimeError('Database dependencies are not installed: sshtunnel/paramiko') from e
        ssh_user = os.environ.get('PA_SSH_USER')
        ssh_pass = os.environ.get('PA_SSH_PASS')
        ssh_key = os.environ.get('PA_SSH_KEY')
        remote_host = db_host or os.environ.get('PA_DB_HOST')
        remote_port = db_port
        # Paramiko DSSKey workaround (as seen elsewhere)
        if not hasattr(paramiko, 'DSSKey'):
            try:
                paramiko.DSSKey = paramiko.RSAKey  # type: ignore[attr-defined]
            except Exception:
                pass
        sshtunnel.SSH_TIMEOUT = 10.0
        sshtunnel.TUNNEL_TIMEOUT = 10.0

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
        # Attach tunnel so callers can close it with connection
        setattr(conn, '_ssh_tunnel', tunnel)
        return conn
    else:
        # Direct connection (no tunnel)
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


def _mysql_init_schema():
    conn = _mysql_connect()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS blog_entries (
                id VARCHAR(255) PRIMARY KEY,
                title VARCHAR(512) NOT NULL,
                author VARCHAR(255) NOT NULL,
                date VARCHAR(32) NOT NULL,
                content MEDIUMTEXT NOT NULL,
                media_json MEDIUMTEXT NULL
            ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
            """
        )
        conn.commit()
    finally:
        _mysql_close(conn)


# Base directories (relative to this file)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BLOG_ENTRIES_DIR = os.path.join(BASE_DIR, 'blog_entries')
COMMENTS_DIR = os.path.join(BASE_DIR, 'blog_comments')
STATE_DIR = os.path.join(BASE_DIR, '.state')  # internal state (auth attempts, reset tokens)
AUTH_ATTEMPTS_FILE = os.path.join(STATE_DIR, 'auth_attempts.json')
RESET_TOKENS_FILE = os.path.join(STATE_DIR, 'reset_tokens.json')

# --- Helpers ---

def _ensure_dirs() -> None:
    os.makedirs(BLOG_ENTRIES_DIR, exist_ok=True)
    os.makedirs(COMMENTS_DIR, exist_ok=True)
    os.makedirs(STATE_DIR, exist_ok=True)


def _read_json_list(path: str) -> list:
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
        return []
    except FileNotFoundError:
        return []
    except Exception:
        return []


def _write_json_list(path: str, items: list) -> None:
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(items, f, indent=2, ensure_ascii=False, default=str)
    os.replace(tmp, path)


# --- Schema / init ---

def init_schema() -> None:
    """Ensure required folders/files exist (no real schema for file backend) or create MySQL schema if enabled."""
    if _use_mysql():
        return _with_retries(_mysql_init_schema)

    def _file_impl():
        _ensure_dirs()
        # Initialize state files if missing
        for p in (AUTH_ATTEMPTS_FILE, RESET_TOKENS_FILE):
            if not os.path.exists(p):
                _write_json_list(p, [])
        return None

    return _with_retries(_file_impl)


# --- Blog entries CRUD (file-based) ---

def _entry_path(entry_key: str) -> str:
    return os.path.join(BLOG_ENTRIES_DIR, f"{entry_key}.json")


def insert_entry(title: str, content: str, author: str, media: Optional[Dict[str, Any]] = None) -> str:
    if _use_mysql():
        def _impl():
            conn = _mysql_connect()
            try:
                cur = conn.cursor()
                # Generate id compatible with file-based one
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                safe_title = "".join(c if c.isalnum() else "_" for c in title)
                entry_key = f"{timestamp}_{safe_title}" if safe_title else timestamp
                media_json = json.dumps(media, ensure_ascii=False) if isinstance(media, dict) else None
                cur.execute(
                    "INSERT INTO blog_entries (id, title, author, date, content, media_json) VALUES (%s,%s,%s,%s,%s,%s)",
                    (
                        entry_key,
                        title,
                        author or 'Anonymous',
                        datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        content,
                        media_json,
                    ),
                )
                conn.commit()
                return entry_key
            finally:
                _mysql_close(conn)
        return _with_retries(_impl)

    _ensure_dirs()
    # Create entry_key like previous code (timestamp + safe title)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_title = "".join(c if c.isalnum() else "_" for c in title)
    entry_key = f"{timestamp}_{safe_title}" if safe_title else timestamp
    data = {
        'id': entry_key,
        'title': title,
        'author': author or 'Anonymous',
        'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'content': content,
        'media': media if isinstance(media, dict) else None,
    }
    with open(_entry_path(entry_key), 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return entry_key


def get_entries() -> List[Dict[str, Any]]:
    if _use_mysql():
        def _impl():
            conn = _mysql_connect()
            try:
                cur = conn.cursor()
                cur.execute("SELECT id, title, author, date, content, media_json FROM blog_entries")
                rows = cur.fetchall()
                results: List[Dict[str, Any]] = []
                for r in rows:
                    entry_id, title, author, date_str, content, media_json = r
                    media = None
                    if media_json:
                        try:
                            media = json.loads(media_json)
                            if not isinstance(media, dict):
                                media = None
                        except Exception:
                            media = None
                    results.append({
                        'id': entry_id,
                        'title': title or 'Untitled',
                        'author': author or 'Anonymous',
                        'date': date_str or '',
                        'content': content or '',
                        'media': media,
                    })
                # Sort by date desc similar to file-based
                def parse_dt(s: str) -> datetime:
                    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y%m%d_%H%M%S"):
                        try:
                            return datetime.strptime(s, fmt)
                        except Exception:
                            continue
                    return datetime.min
                results.sort(key=lambda e: parse_dt(e.get('date', '')), reverse=True)
                return results
            finally:
                _mysql_close(conn)
        return _with_retries(_impl)

    _ensure_dirs()
    results: List[Dict[str, Any]] = []
    try:
        for name in os.listdir(BLOG_ENTRIES_DIR):
            if not name.lower().endswith('.json'):
                continue
            path = os.path.join(BLOG_ENTRIES_DIR, name)
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if not isinstance(data, dict):
                    continue
                entry_id = data.get('id') or os.path.splitext(name)[0]
                results.append({
                    'id': entry_id,
                    'title': data.get('title') or 'Untitled',
                    'author': data.get('author') or 'Anonymous',
                    'date': data.get('date') or '',
                    'content': data.get('content') or '',
                    'media': data.get('media') if isinstance(data.get('media'), dict) else None,
                })
            except Exception:
                continue
        # Sort by date descending when possible
        def parse_dt(s: str) -> datetime:
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y%m%d_%H%M%S"):
                try:
                    return datetime.strptime(s, fmt)
                except Exception:
                    continue
            return datetime.min
        results.sort(key=lambda e: parse_dt(e.get('date', '')), reverse=True)
    except Exception:
        pass
    return results


def get_entry(entry_id: str) -> Optional[Dict[str, Any]]:
    if _use_mysql():
        def _impl():
            conn = _mysql_connect()
            try:
                cur = conn.cursor()
                cur.execute("SELECT id, title, author, date, content, media_json FROM blog_entries WHERE id=%s", (entry_id,))
                row = cur.fetchone()
                if not row:
                    return None
                entry_id2, title, author, date_str, content, media_json = row
                media = None
                if media_json:
                    try:
                        media = json.loads(media_json)
                        if not isinstance(media, dict):
                            media = None
                    except Exception:
                        media = None
                return {
                    'id': entry_id2,
                    'title': title or 'Untitled',
                    'author': author or 'Anonymous',
                    'date': date_str or '',
                    'content': content or '',
                    'media': media,
                }
            finally:
                _mysql_close(conn)
        return _with_retries(_impl)

    _ensure_dirs()
    path = _entry_path(entry_id)
    if not os.path.exists(path):
        return None
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return None
        return {
            'id': entry_id,
            'title': data.get('title') or 'Untitled',
            'author': data.get('author') or 'Anonymous',
            'date': data.get('date') or '',
            'content': data.get('content') or '',
            'media': data.get('media') if isinstance(data.get('media'), dict) else None,
        }
    except Exception:
        return None


def update_entry(entry_id: str, title: str, content: str, author: str, media: Optional[Dict[str, Any]] = None) -> bool:
    if _use_mysql():
        def _impl():
            conn = _mysql_connect()
            try:
                cur = conn.cursor()
                # Fetch existing to preserve date if needed
                cur.execute("SELECT date FROM blog_entries WHERE id=%s", (entry_id,))
                row = cur.fetchone()
                if not row:
                    return False
                date_str = row[0]
                media_json = json.dumps(media, ensure_ascii=False) if isinstance(media, dict) else None
                cur.execute(
                    "UPDATE blog_entries SET title=%s, author=%s, date=%s, content=%s, media_json=%s WHERE id=%s",
                    (
                        title,
                        author or 'Anonymous',
                        date_str or datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        content,
                        media_json,
                        entry_id,
                    ),
                )
                conn.commit()
                return cur.rowcount > 0
            finally:
                _mysql_close(conn)
        return _with_retries(_impl)

    _ensure_dirs()
    existing = get_entry(entry_id)
    if not existing:
        return False
    updated = {
        'id': entry_id,
        'title': title or existing['title'],
        'author': author or existing['author'],
        'date': existing['date'] or datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'content': content,
        'media': media if isinstance(media, dict) else existing.get('media'),
    }
    try:
        with open(_entry_path(entry_id), 'w', encoding='utf-8') as f:
            json.dump(updated, f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False


def delete_entry(entry_id: str) -> bool:
    if _use_mysql():
        def _impl():
            conn = _mysql_connect()
            try:
                cur = conn.cursor()
                cur.execute("DELETE FROM blog_entries WHERE id=%s", (entry_id,))
                conn.commit()
                return cur.rowcount > 0
            finally:
                _mysql_close(conn)
        return _with_retries(_impl)

    _ensure_dirs()
    path = _entry_path(entry_id)
    if not os.path.exists(path):
        return False
    try:
        os.remove(path)
        return True
    except Exception:
        return False


# --- Authentication attempt tracking (file-based) ---

def log_auth_attempt(feature: str, ip: str | None, success: bool | None, note: str | None = None) -> None:
    _ensure_dirs()
    items = _read_json_list(AUTH_ATTEMPTS_FILE)
    items.append({
        'feature': feature,
        'ts': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'ip': ip,
        'success': (1 if success is True else 0 if success is False else None),
        'note': note,
    })
    _write_json_list(AUTH_ATTEMPTS_FILE, items)


def _iter_attempts(feature: str):
    items = _read_json_list(AUTH_ATTEMPTS_FILE)
    for it in items:
        if isinstance(it, dict) and it.get('feature') == feature:
            yield it


def _parse_ts(val) -> Optional[datetime]:
    if isinstance(val, datetime):
        return val
    if isinstance(val, str):
        for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d'):
            try:
                return datetime.strptime(val, fmt)
            except Exception:
                continue
    return None


def get_last_lock_time(feature: str) -> Optional[datetime]:
    last: Optional[datetime] = None
    for it in _iter_attempts(feature):
        if it.get('note') == 'LOCK':
            ts = _parse_ts(it.get('ts'))
            if ts and (last is None or ts > last):
                last = ts
    return last


def get_last_unlock_time(feature: str) -> Optional[datetime]:
    last: Optional[datetime] = None
    for it in _iter_attempts(feature):
        if it.get('note') == 'UNLOCK':
            ts = _parse_ts(it.get('ts'))
            if ts and (last is None or ts > last):
                last = ts
    return last


def record_unlock(feature: str) -> None:
    log_auth_attempt(feature, None, None, 'UNLOCK')


def is_locked(feature: str) -> tuple[bool, Optional[datetime]]:
    last_lock = get_last_lock_time(feature)
    if not last_lock:
        return False, None
    last_unlock = get_last_unlock_time(feature)
    if last_unlock and last_unlock >= last_lock:
        return False, None
    until = last_lock + timedelta(hours=24)
    if datetime.now() < until:
        return True, until
    return False, None


def get_consecutive_fail_count(feature: str) -> int:
    # Read attempts for feature ordered by ts desc
    attempts = list(_iter_attempts(feature))
    # Sort descending by ts
    def key_ts(it):
        dt = _parse_ts(it.get('ts')) or datetime.min
        return dt
    attempts.sort(key=key_ts, reverse=True)
    fails = 0
    for it in attempts:
        if it.get('note') is not None:
            # Skip special events
            continue
        success_val = it.get('success')
        if success_val == 1:
            break
        if success_val == 0:
            fails += 1
    return fails


# --- Reset token helpers (file-based) ---

def create_reset_token(feature: str, lifetime_hours: int = 24) -> str:
    _ensure_dirs()
    token = secrets.token_urlsafe(32)
    now = datetime.now()
    expires = now + timedelta(hours=lifetime_hours)
    items = _read_json_list(RESET_TOKENS_FILE)
    items.append({
        'feature': feature,
        'token': token,
        'ts': now.strftime('%Y-%m-%d %H:%M:%S'),
        'expires_at': expires.strftime('%Y-%m-%d %H:%M:%S'),
        'used': 0,
    })
    _write_json_list(RESET_TOKENS_FILE, items)
    return token


def get_reset_by_token(token: str) -> Optional[dict]:
    items = _read_json_list(RESET_TOKENS_FILE)
    for it in items:
        if isinstance(it, dict) and it.get('token') == token:
            # Return a copy with parsed types similar to DB row mapping
            return {
                'id': None,
                'feature': it.get('feature'),
                'token': it.get('token'),
                'ts': it.get('ts'),
                'expires_at': it.get('expires_at'),
                'used': bool(it.get('used')),
            }
    return None


def mark_reset_used(token: str) -> None:
    items = _read_json_list(RESET_TOKENS_FILE)
    changed = False
    for it in items:
        if isinstance(it, dict) and it.get('token') == token:
            it['used'] = 1
            changed = True
            break
    if changed:
        _write_json_list(RESET_TOKENS_FILE, items)



def comments_count(entry_id: str) -> int:
    """Return number of comments for an entry.
    - File backend: count items in blog_comments/<entry_id>.json
    - Optional MySQL backend: query COUNT(*) from blog_comments (returns 0 on error)
    """
    if _use_mysql():
        # Best-effort SQL count; if table is missing or any error occurs, return 0
        def _impl():
            try:
                conn = _mysql_connect()
                try:
                    cur = conn.cursor()
                    cur.execute("SELECT COUNT(*) FROM blog_comments WHERE entry_id=%s", (entry_id,))
                    row = cur.fetchone()
                    return int(row[0]) if row and row[0] is not None else 0
                finally:
                    _mysql_close(conn)
            except Exception:
                return 0
        try:
            return int(_with_retries(_impl))
        except Exception:
            return 0

    # File-based counting
    _ensure_dirs()
    path = os.path.join(COMMENTS_DIR, f"{entry_id}.json")
    try:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if isinstance(data, list):
                return len(data)
    except Exception:
        return 0
    return 0
