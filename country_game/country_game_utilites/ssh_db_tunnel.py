from typing import Optional, Tuple
import atexit
import weakref
import paramiko

# Paramiko v3+ compatibility: sshtunnel expects paramiko.DSSKey which was removed.
if not hasattr(paramiko, "DSSKey"):
    # Fallback to RSAKey to satisfy attribute checks; we authenticate via password.
    try:
        paramiko.DSSKey = paramiko.RSAKey  # type: ignore[attr-defined]
    except Exception:
        pass

import MySQLdb
import sshtunnel

# Configure timeouts
sshtunnel.SSH_TIMEOUT = 10.0
sshtunnel.TUNNEL_TIMEOUT = 10.0

SSH_HOST = 'ssh.pythonanywhere.com'
SSH_USERNAME = 'spade605'
SSH_PASSWORD = 'Beholder20!'
REMOTE_DB_HOST = 'spade605.mysql.pythonanywhere-services.com'
REMOTE_DB_PORT = 3306
DB_USER = 'spade605'
DB_PASSWORD = 'Darklove90!'
DB_NAME = 'spade605$county_game_server'

# Track active tunnels so we can shut them down on interpreter exit
_ACTIVE_TUNNEL_REFS = set()

def _register_tunnel(tunnel: object) -> None:
    try:
        _ACTIVE_TUNNEL_REFS.add(weakref.ref(tunnel))
    except Exception:
        pass

@atexit.register
def _cleanup_tunnels_at_exit() -> None:
    # Best-effort: stop any still-active tunnels to avoid background thread cleanup errors on Py3.13
    try:
        refs = list(_ACTIVE_TUNNEL_REFS)
    except Exception:
        refs = []
    for r in refs:
        try:
            t = r() if callable(r) else None  # type: ignore[misc]
            if t is None:
                continue
            # Some sshtunnel objects provide is_active; guard generously
            if getattr(t, 'is_active', False):
                try:
                    t.stop()
                except Exception:
                    pass
        except Exception:
            pass


def _make_connection_through_tunnel(db_user: str, db_password: str, db_name: str) -> Tuple[Optional[object], Optional[callable]]:
    """Low-level helper: returns (conn, closer) or (None, None) on failure.
    The closer is idempotent and will stop the tunnel and close the connection.
    """
    try:
        # Create and start the tunnel explicitly so it persists while the DB connection is in use
        tunnel = sshtunnel.SSHTunnelForwarder(
            SSH_HOST,
            ssh_username=SSH_USERNAME,
            ssh_password=SSH_PASSWORD,
            remote_bind_address=(REMOTE_DB_HOST, REMOTE_DB_PORT),
            set_keepalive=15,
        )
        tunnel.start()
        _register_tunnel(tunnel)

        # Create MySQL connection through the local forwarded port
        conn = MySQLdb.connect(
            user=db_user,
            passwd=db_password,
            host='127.0.0.1',
            port=tunnel.local_bind_port,
            db=db_name,
            connect_timeout=10,
            charset='utf8mb4',
            use_unicode=True,
        )
        # Enable auto-reconnect on ping
        try:
            conn.ping(True)  # type: ignore[attr-defined]
        except Exception:
            pass

        # Provide compatibility: allow cursor(dictionary=True) like mysql.connector
        try:
            import MySQLdb.cursors as _dbcursors
            _orig_cursor = conn.cursor  # type: ignore[attr-defined]
            def _cursor_wrapper(*args, **kwargs):  # type: ignore[no-untyped-def]
                if 'dictionary' in kwargs:
                    use_dict = bool(kwargs.pop('dictionary'))
                    if use_dict:
                        try:
                            return _orig_cursor(_dbcursors.DictCursor)
                        except Exception:
                            return _orig_cursor(*args, **kwargs)
                return _orig_cursor(*args, **kwargs)
            try:
                setattr(conn, 'cursor', _cursor_wrapper)
            except Exception:
                pass
        except Exception:
            pass

        # Define an idempotent closer
        def _closer() -> None:
            try:
                try:
                    conn.close()
                except Exception:
                    pass
                try:
                    if getattr(tunnel, 'is_active', False):
                        tunnel.stop()
                except Exception:
                    pass
            except Exception:
                pass

        # Also tie tunnel lifetime to the connection's close(), but keep our own closer too
        original_close = conn.close
        def close_and_stop_tunnel(*args, **kwargs):  # type: ignore[no-untyped-def]
            try:
                return original_close(*args, **kwargs)
            finally:
                try:
                    if getattr(tunnel, 'is_active', False):
                        tunnel.stop()
                except Exception:
                    pass
        try:
            conn.close = close_and_stop_tunnel  # type: ignore[assignment]
        except Exception:
            pass

        # Expose the tunnel for debugging if needed
        try:
            setattr(conn, "_ssh_tunnel", tunnel)
        except Exception:
            pass

        return conn, _closer
    except Exception as e:
        msg = f"Error connecting to remote database: {e!r}"
        print(msg)
        if "DSSKey" in str(e):
            print("Hint: Paramiko v3 removed DSSKey; ensure the compatibility shim runs before importing sshtunnel.")
        return None, None


def connect_via_tunnel() -> Optional[object]:
    """Open an SSH tunnel and connect to the remote MySQL database.

    Returns a live MySQLdb connection if successful; the caller is responsible for closing it.
    Returns None if a connection could not be established.
    The SSH tunnel remains open for the lifetime of the returned connection and
    will be closed automatically when conn.close() is called.
    """
    conn, _ = _make_connection_through_tunnel(DB_USER, DB_PASSWORD, DB_NAME)
    return conn


def get_connector_connection_via_tunnel(db_user: Optional[str] = None,
                                         db_password: Optional[str] = None,
                                         db_name: Optional[str] = None) -> Tuple[Optional[object], Optional[callable]]:
    """Return (connection, closer) for code expecting mysql.connector-like behavior.
    The caller should call closer() when done; connection.close() also stops the tunnel.
    """
    user = db_user or DB_USER
    pwd = db_password or DB_PASSWORD
    name = db_name or DB_NAME
    return _make_connection_through_tunnel(user, pwd, name)
