from typing import Optional, Dict, Any, List

SSH_HOST = 'ssh.pythonanywhere.com'
SSH_USERNAME = 'spade605'
SSH_PASSWORD = 'Beholder20!'
REMOTE_DB_HOST = 'spade605.mysql.pythonanywhere-services.com'
REMOTE_DB_PORT = 3306
DB_USER = 'spade605'
DB_PASSWORD = 'Darklove90!'
DB_NAME = 'spade605$blog'


def _open_connection():
    """Open a DB connection via SSH tunnel.

    Imports heavy/optional dependencies lazily so that importing this module
    does not crash in environments where paramiko/sshtunnel/MySQLdb are not
    installed. Callers should expect RuntimeError if the DB layer is
    unavailable; route code already catches and logs such errors.
    """
    try:
        import paramiko  # type: ignore
        import MySQLdb  # type: ignore
        import sshtunnel  # type: ignore
    except ImportError as e:
        raise RuntimeError("Database dependencies are not installed (paramiko/sshtunnel/MySQLdb)") from e

    # Paramiko v3+ compatibility for sshtunnel
    if not hasattr(paramiko, "DSSKey"):
        try:
            paramiko.DSSKey = paramiko.RSAKey  # type: ignore[attr-defined]
        except Exception:
            pass

    # Configure sshtunnel timeouts
    sshtunnel.SSH_TIMEOUT = 10.0
    sshtunnel.TUNNEL_TIMEOUT = 10.0

    tunnel = sshtunnel.SSHTunnelForwarder(
        (SSH_HOST, 22),
        ssh_username=SSH_USERNAME,
        ssh_password=SSH_PASSWORD,
        remote_bind_address=(REMOTE_DB_HOST, REMOTE_DB_PORT),
        set_keepalive=15,
        allow_agent=False,
        host_pkey_directories=[],
    )
    tunnel.start()
    # Guard: ensure tunnel is active and local port assigned
    if not getattr(tunnel, 'is_active', False) or not getattr(tunnel, 'local_bind_port', None):
        # Best-effort stop and raise a clearer error
        try:
            tunnel.stop()
        except Exception:
            pass
        raise RuntimeError('SSH tunnel failed to start or no local_bind_port assigned')
    conn = MySQLdb.connect(
        user=DB_USER,
        passwd=DB_PASSWORD,
        host='127.0.0.1',
        port=tunnel.local_bind_port,
        db=DB_NAME,
        connect_timeout=10,
        charset='utf8mb4',
        use_unicode=True,
    )
    return conn, tunnel


def _close(conn, tunnel):
    try:
        conn.close()
    except Exception:
        pass
    try:
        if getattr(tunnel, 'is_active', False):
            tunnel.stop()
    except Exception:
        pass


def init_schema() -> None:
    conn, tunnel = _open_connection()
    try:
        cur = conn.cursor()
        # Blog entries table
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
        # Auth attempts table for Grammar Checker (and potentially other features)
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS auth_attempts (
                id INT AUTO_INCREMENT PRIMARY KEY,
                feature VARCHAR(64) NOT NULL,
                ts DATETIME NOT NULL,
                ip VARCHAR(64) NULL,
                success TINYINT(1) NULL,
                note VARCHAR(255) NULL
            ) CHARACTER SET utf8mb4;
            """
        )
        # Reset tokens table for owner-triggered unlocks
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS reset_tokens (
                id INT AUTO_INCREMENT PRIMARY KEY,
                feature VARCHAR(64) NOT NULL,
                token VARCHAR(128) NOT NULL UNIQUE,
                ts DATETIME NOT NULL,
                expires_at DATETIME NOT NULL,
                used TINYINT(1) NOT NULL DEFAULT 0
            ) CHARACTER SET utf8mb4;
            """
        )
        conn.commit()
    finally:
        _close(conn, tunnel)


def insert_entry(title: str, content: str, author: str, media: Optional[Dict[str, Any]] = None) -> str:
    import datetime
    # Create entry_key to keep compatibility with file-based id (timestamp based)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_title = "".join(c if c.isalnum() else "_" for c in title)
    entry_key = f"{timestamp}_{safe_title}"

    conn, tunnel = _open_connection()
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
        _close(conn, tunnel)


def get_entries() -> List[Dict[str, Any]]:
    conn, tunnel = _open_connection()
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
        _close(conn, tunnel)


def get_entry(entry_id: str) -> Optional[Dict[str, Any]]:
    conn, tunnel = _open_connection()
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
        _close(conn, tunnel)


def update_entry(entry_id: str, title: str, content: str, author: str, media: Optional[Dict[str, Any]] = None) -> bool:
    """Update an existing entry by entry_key. Preserves created_at."""
    conn, tunnel = _open_connection()
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
        _close(conn, tunnel)


def delete_entry(entry_id: str) -> bool:
    conn, tunnel = _open_connection()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM entries WHERE entry_key=%s", (entry_id,))
        conn.commit()
        return cur.rowcount > 0
    finally:
        _close(conn, tunnel)


# --- Authentication attempt tracking for Grammar Checker ---
from datetime import datetime, timedelta

def log_auth_attempt(feature: str, ip: str | None, success: bool | None, note: str | None = None) -> None:
    """Insert an authentication attempt record.

    success: True for correct password, False for wrong password, None for special events
    (e.g., a lock event recorded with note='LOCK').
    """
    conn, tunnel = _open_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO auth_attempts (feature, ts, ip, success, note)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (feature, datetime.now(), ip, int(success) if success is not None else None, note)
        )
        conn.commit()
    finally:
        _close(conn, tunnel)


def get_last_lock_time(feature: str) -> Optional[datetime]:
    """Return the timestamp of the most recent LOCK event, or None."""
    conn, tunnel = _open_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT ts FROM auth_attempts
            WHERE feature=%s AND note='LOCK'
            ORDER BY ts DESC LIMIT 1
            """,
            (feature,)
        )
        row = cur.fetchone()
        return row[0] if row else None
    finally:
        _close(conn, tunnel)


def get_last_unlock_time(feature: str) -> Optional[datetime]:
    """Return the timestamp of the most recent UNLOCK event, or None."""
    conn, tunnel = _open_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT ts FROM auth_attempts
            WHERE feature=%s AND note='UNLOCK'
            ORDER BY ts DESC LIMIT 1
            """,
            (feature,)
        )
        row = cur.fetchone()
        return row[0] if row else None
    finally:
        _close(conn, tunnel)


def record_unlock(feature: str) -> None:
    """Record an UNLOCK event in auth_attempts to bypass an active lock."""
    conn, tunnel = _open_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO auth_attempts (feature, ts, ip, success, note)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (feature, datetime.now(), None, None, 'UNLOCK')
        )
        conn.commit()
    finally:
        _close(conn, tunnel)


def is_locked(feature: str) -> tuple[bool, Optional[datetime]]:
    """Check if feature is locked based on last LOCK event within 24 hours,
    honoring any newer UNLOCK event that clears the lock early.
    """
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
    """Count consecutive failed attempts since the last success, most recent first."""
    conn, tunnel = _open_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT success FROM auth_attempts
            WHERE feature=%s AND note IS NULL
            ORDER BY ts DESC LIMIT 10
            """,
            (feature,)
        )
        fails = 0
        for (success_val,) in cur.fetchall():
            if success_val is None:
                # Skip unexpected rows
                continue
            if success_val == 1:
                break
            else:
                fails += 1
        return fails
    finally:
        _close(conn, tunnel)


# --- Reset token helpers ---
import secrets

def create_reset_token(feature: str, lifetime_hours: int = 24) -> str:
    """Create and store a reset token for the given feature and return it."""
    token = secrets.token_urlsafe(32)
    now = datetime.now()
    expires = now + timedelta(hours=lifetime_hours)
    conn, tunnel = _open_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO reset_tokens (feature, token, ts, expires_at, used)
            VALUES (%s, %s, %s, %s, 0)
            """,
            (feature, token, now, expires)
        )
        conn.commit()
    finally:
        _close(conn, tunnel)
    return token


def get_reset_by_token(token: str) -> Optional[dict]:
    conn, tunnel = _open_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, feature, token, ts, expires_at, used
            FROM reset_tokens WHERE token=%s
            """,
            (token,)
        )
        row = cur.fetchone()
        if not row:
            return None
        return {
            'id': row[0],
            'feature': row[1],
            'token': row[2],
            'ts': row[3],
            'expires_at': row[4],
            'used': bool(row[5]),
        }
    finally:
        _close(conn, tunnel)


def mark_reset_used(token: str) -> None:
    conn, tunnel = _open_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE reset_tokens SET used=1 WHERE token=%s
            """,
            (token,)
        )
        conn.commit()
    finally:
        _close(conn, tunnel)
