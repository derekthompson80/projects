"""
SSH Tunnel utility for connecting to MySQL via sshtunnel following
https://github.com/pahaz/sshtunnel/blob/master/Troubleshoot.rst guidance.

This module provides a minimal helper to establish an SSH tunnel to a remote
MySQL server (e.g., PythonAnywhere) and return a mysql.connector connection
bound to the local forwarded port.

Usage environment variables (PowerShell examples):
  $env:CG_USE_SSH_TUNNEL='true'
  $env:CG_SSH_HOST='yourusername.pythonanywhere.com'
  $env:CG_SSH_PORT='22'
  $env:CG_SSH_USER='yourusername'
  # One of the following for SSH auth:
  $env:CG_SSH_PASSWORD='your_web_password'         # or
  $env:CG_SSH_PKEY='C:\\Path\\to\\private_key'   # optional

  $env:CG_REMOTE_DB_HOST='yourusername.mysql.pythonanywhere-services.com'
  $env:CG_REMOTE_DB_PORT='3306'

  $env:CG_DB_USER='yourusername'
  $env:CG_DB_PASSWORD='db_password'

This helper avoids the common "Error: 2003 (HY000): Can't connect to MySQL server on '127.0.0.1:3306'"
by ensuring a local tunnel endpoint is created and used.
"""
from __future__ import annotations

import os
import socket
import time
from contextlib import contextmanager
from typing import Callable, Optional, Tuple

from sshtunnel import SSHTunnelForwarder  # type: ignore
import mysql.connector

# Default local bind host and an ephemeral port (0 lets OS choose a free port)
LOCAL_BIND_HOST = '127.0.0.1'


def _env(name: str, default: Optional[str] = None) -> Optional[str]:
    v = os.getenv(name)
    return v if v is not None and v != '' else default


def _pick_free_port(host: str = LOCAL_BIND_HOST) -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((host, 0))
        return s.getsockname()[1]


def get_connector_connection_via_tunnel(
    db_user: Optional[str],
    db_password: Optional[str],
    db_name: Optional[str] = None,
) -> Tuple[mysql.connector.MySQLConnection, Callable[[], None]]:
    """
    Open an SSH tunnel to the remote DB host and return a mysql.connector
    connection along with a close() function that will stop the tunnel.

    Returns: (connection, close_func)
    """
    ssh_host = _env('CG_SSH_HOST')
    ssh_port = int(_env('CG_SSH_PORT', '22'))
    ssh_user = _env('CG_SSH_USER')
    ssh_password = _env('CG_SSH_PASSWORD')
    ssh_pkey = _env('CG_SSH_PKEY')

    remote_db_host = _env('CG_REMOTE_DB_HOST')
    remote_db_port = int(_env('CG_REMOTE_DB_PORT', '3306'))

    if not ssh_host or not ssh_user or not remote_db_host:
        raise RuntimeError('Missing SSH/DB envs: CG_SSH_HOST, CG_SSH_USER, CG_REMOTE_DB_HOST')

    # Allocate a free local port to avoid collisions with running MySQL
    local_port = _pick_free_port()

    # Build SSHTunnelForwarder arguments per Troubleshoot.rst best practices
    tunnel_kwargs = {
        'ssh_address_or_host': (ssh_host, ssh_port),
        'ssh_username': ssh_user,
        'remote_bind_address': (remote_db_host, remote_db_port),
        'local_bind_address': (LOCAL_BIND_HOST, local_port),
        'mute_exceptions': False,
    }

    # Provide auth either via password or private key
    if ssh_password:
        tunnel_kwargs['ssh_password'] = ssh_password
    if ssh_pkey:
        tunnel_kwargs['ssh_pkey'] = ssh_pkey

    server = SSHTunnelForwarder(**tunnel_kwargs)
    server.start()

    # Wait a moment to ensure the tunnel is ready
    time.sleep(0.2)

    # Connect mysql.connector to the local forwarded port
    conn = mysql.connector.connect(
        user=db_user,
        password=db_password,
        host=LOCAL_BIND_HOST,
        port=server.local_bind_port,
        database=db_name if db_name else None,
        raise_on_warnings=True,
    )

    def _close():
        try:
            try:
                conn.close()
            except Exception:
                pass
        finally:
            try:
                server.stop()
            except Exception:
                pass

    return conn, _close


@contextmanager
def connector_connection_via_tunnel(db_user: Optional[str], db_password: Optional[str], db_name: Optional[str] = None):
    conn, close_func = get_connector_connection_via_tunnel(db_user, db_password, db_name)
    try:
        yield conn
    finally:
        close_func()
