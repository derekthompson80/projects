import os
from typing import Callable, Tuple, Optional

# We prefer mysql.connector in this project
import mysql.connector

try:
    from sshtunnel import SSHTunnelForwarder  # type: ignore
    import sshtunnel
    sshtunnel.SSH_TIMEOUT = 10.0
    sshtunnel.TUNNEL_TIMEOUT = 10.0
    # Work around Paramiko>=3 removal of DSSKey which older sshtunnel still imports
    try:
        import paramiko  # type: ignore
        if not hasattr(paramiko, 'DSSKey'):
            class _DummyDSSKey(paramiko.PKey):  # type: ignore
                @classmethod
                def from_private_key_file(cls, filename, password=None):  # type: ignore
                    raise NotImplementedError("DSA keys are not supported by Paramiko >= 3")
            paramiko.DSSKey = _DummyDSSKey  # type: ignore
    except Exception:
        # If paramiko import fails here, sshtunnel will likely fail later anyway
        pass
except Exception as e:  # pragma: no cover
    SSHTunnelForwarder = None  # type: ignore


class TunnelNotAvailable(Exception):
    pass


def _get_env(name: str, default: Optional[str] = None) -> Optional[str]:
    v = os.getenv(name)
    return v if v is not None and str(v).strip() != "" else default


def get_connector_connection_via_tunnel(
    db_user: Optional[str] = None,
    db_password: Optional[str] = None,
    db_name: Optional[str] = None,
) -> Tuple[mysql.connector.MySQLConnection, Callable[[], None]]:
    """
    Open an SSH tunnel to PythonAnywhere and return a mysql.connector connection
    that uses the tunnel, plus a close() function to tear everything down.

    Required environment variables (with sensible defaults for the user's request):
    - CG_SSH_HOST: SSH hostname (eg yourusername.pythonanywhere.com)
    - CG_SSH_USER: SSH username (eg yourusername)
    - CG_SSH_PASSWORD: SSH password (web login password) OR CG_SSH_PKEY: path to private key
    - CG_REMOTE_DB_HOST: Remote MySQL host (eg yourusername.mysql.pythonanywhere-services.com)
    - CG_REMOTE_DB_PORT: Remote MySQL port (default 3306)

    Database credentials can be passed explicitly or via env:
    - CG_DB_USER, CG_DB_PASSWORD, CG_DB_NAME

    Also supported aliases for convenience:
    - PA_SSH_HOST, PA_SSH_USER, PA_SSH_PASSWORD, PYTHONANYWHERE_PASSWORD, PA_PASSWORD
    - PA_REMOTE_DB_HOST
    - CG_SSH_PKEY / PA_SSH_PKEY (and CG_SSH_PKEY_PASSWORD / PA_SSH_PKEY_PASSWORD)
    """
    if SSHTunnelForwarder is None:
        raise TunnelNotAvailable("sshtunnel is not installed or failed to import")

    # SSH details
    ssh_host = _get_env('CG_SSH_HOST', _get_env('PA_SSH_HOST'))
    ssh_user = _get_env('CG_SSH_USER') or _get_env('PA_SSH_USER') or _get_env('PA_USERNAME') or 'spade605'

    # Accept several password aliases; fall back to known PA website password if not set
    ssh_password = (
        _get_env('CG_SSH_PASSWORD')
        or _get_env('PA_SSH_PASSWORD')
        or _get_env('PYTHONANYWHERE_PASSWORD')
        or _get_env('PA_PASSWORD')
        or 'Beholder20!'
    )
    # Optional key-based auth
    ssh_pkey = _get_env('CG_SSH_PKEY') or _get_env('PA_SSH_PKEY')
    ssh_pkey_password = _get_env('CG_SSH_PKEY_PASSWORD') or _get_env('PA_SSH_PKEY_PASSWORD')

    # Remote DB endpoint
    remote_db_host = _get_env('CG_REMOTE_DB_HOST', _get_env('PA_REMOTE_DB_HOST')) or 'spade605.mysql.pythonanywhere-services.com'
    remote_db_port = int(_get_env('CG_REMOTE_DB_PORT', '3306') or '3306')

    # Fill DB creds (defaults align with the user's provided details)
    db_user = db_user or _get_env('CG_DB_USER') or _get_env('DB_USER') or 'spade605'
    db_password = db_password or _get_env('CG_DB_PASSWORD') or _get_env('DB_PASSWORD') or 'Darklove90!'

    # Only set a database if one was explicitly provided, otherwise leave None for server-level ops
    selected_db = db_name if db_name is not None else None
    if selected_db is None:
        # If the caller did not specify, do not force default DB; let MySQL connect without selecting a DB
        pass
    else:
        # If caller provided a value (even empty string), try to resolve defaults
        if not selected_db:
            selected_db = _get_env('CG_DB_NAME') or 'spade605$county_game_server'

    # If not provided, apply a sensible default for PythonAnywhere SSH host
    if not ssh_host:
        ssh_host = _get_env('CG_PREFERRED_SSH_HOST') or 'ssh.pythonanywhere.com'

    # Validate required fields; DB name is only required when selected_db is not None
    base_missing = [
        ('CG_SSH_HOST', ssh_host),
        ('CG_SSH_USER', ssh_user),
        ('CG_REMOTE_DB_HOST', remote_db_host),
        ('CG_DB_USER', db_user),
        ('CG_DB_PASSWORD', db_password),
    ]
    if selected_db is not None:
        base_missing.append(('CG_DB_NAME', selected_db))

    missing_keys = [k for k, v in base_missing if not v]

    # Ensure at least one SSH auth method is provided
    has_auth = bool(ssh_password) or bool(ssh_pkey)
    if not has_auth:
        missing_keys.append('CG_SSH_PASSWORD or CG_SSH_PKEY')

    if missing_keys:
        raise ValueError(
            "Missing required env/config for SSH tunnel: " + ", ".join(missing_keys)
        )

    # Build the tunnel with either password or key-based auth
    tunnel_kwargs = {
        'ssh_username': ssh_user,
        'remote_bind_address': (remote_db_host, remote_db_port),
        'local_bind_address': ('127.0.0.1', 0),  # auto-pick local port
    }
    if ssh_pkey:
        tunnel_kwargs['ssh_pkey'] = ssh_pkey
        if ssh_pkey_password:
            tunnel_kwargs['ssh_private_key_password'] = ssh_pkey_password
    else:
        tunnel_kwargs['ssh_password'] = ssh_password

    tunnel = SSHTunnelForwarder((ssh_host, 22), **tunnel_kwargs)
    tunnel.start()

    # Build mysql.connector connection via 127.0.0.1 and the tunnel's local port
    conn_kwargs = dict(
        user=db_user,
        password=db_password,
        host='127.0.0.1',
        port=tunnel.local_bind_port,
        raise_on_warnings=True,
    )
    if selected_db is not None:
        conn_kwargs['database'] = selected_db
    conn = mysql.connector.connect(**conn_kwargs)

    def _close():
        try:
            try:
                if conn.is_connected():
                    conn.close()
            except Exception:
                pass
        finally:
            try:
                tunnel.stop()
            except Exception:
                pass

    return conn, _close


def quick_test_connection() -> bool:
    """Quickly open a tunnel and run SELECT 1; returns True if successful."""
    conn, close_func = get_connector_connection_via_tunnel()
    try:
        cur = conn.cursor()
        cur.execute('SELECT 1')
        cur.fetchone()
        return True
    finally:
        close_func()
