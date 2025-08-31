"""
PythonAnywhere MySQL over SSH tunnel test

This script opens an SSH tunnel to PythonAnywhere and connects to the MySQL database
hosted there, then runs a simple query to confirm the connection.

Requirements (install if missing):
  pip install sshtunnel mysql-connector-python python-dotenv

Usage:
  python projects\pythonanywhere_mysql_tunnel_test.py

Security note:
  Credentials are hardcoded per the task request. For production, move them to
  environment variables or a .env file and load via python-dotenv.
"""
from __future__ import annotations

import sys
import os
import logging
from contextlib import closing

# Workaround for Paramiko 3.x where DSSKey was removed but older sshtunnel expects it
try:
    import paramiko  # type: ignore
    if not hasattr(paramiko, "DSSKey"):
        # Monkey-patch to satisfy sshtunnel's key map; not used when password auth
        paramiko.DSSKey = paramiko.RSAKey  # type: ignore[attr-defined]
except Exception:
    # If paramiko import fails, sshtunnel will also fail; let the next import raise a clearer msg
    pass

try:
    from sshtunnel import SSHTunnelForwarder  # type: ignore
except Exception as e:
    print("Missing dependency: sshtunnel. Install with: pip install sshtunnel")
    raise

try:
    import mysql.connector  # type: ignore
except Exception:
    print("Missing dependency: mysql-connector-python. Install with: pip install mysql-connector-python")
    raise

# Optional: configure sshtunnel timeouts
try:
    import sshtunnel as _ssht  # type: ignore
    _ssht.SSH_TIMEOUT = 10.0
    _ssht.TUNNEL_TIMEOUT = 10.0
except Exception:
    pass

# Provided credentials/details (configurable via environment variables)
# SSH configuration
SSH_HOST = os.getenv("PA_SSH_HOST", "ssh.pythonanywhere.com")  # Standard SSH endpoint for PythonAnywhere
SSH_PORT = int(os.getenv("PA_SSH_PORT", "22"))
SSH_USERNAME = os.getenv("PA_SSH_USERNAME", "spade605")
SSH_PASSWORD = os.getenv("PA_SSH_PASSWORD", "Beholder20!")  # PythonAnywhere WEBSITE password (leave empty if using key)
SSH_PKEY = os.getenv("PA_SSH_PKEY")  # Path to private key file (e.g., C:\\Users\\spade\\.ssh\\id_ed25519)
SSH_PKEY_PASSPHRASE = os.getenv("PA_SSH_PKEY_PASSPHRASE")

# Database configuration
DB_REMOTE_HOST = os.getenv("PA_DB_HOST", "spade605.mysql.pythonanywhere-services.com")
DB_REMOTE_PORT = int(os.getenv("PA_DB_PORT", "3306"))
DB_USER = os.getenv("PA_DB_USER", "spade605")
DB_PASSWORD = os.getenv("PA_DB_PASSWORD", "Darklove90!")
DB_NAME = os.getenv("PA_DB_NAME", "spade605$county_game_server")

# Choose auth method: prefer password if provided; else try private key
if SSH_PASSWORD:
    SSH_PKEY = None
else:
    # If SSH_PKEY not set, try default local key path
    if not SSH_PKEY:
        _default_pkey = os.path.expanduser(r"~\.ssh\id_ed25519")
        if os.path.exists(_default_pkey):
            SSH_PKEY = _default_pkey


def test_connection() -> int:
    # Enable debug logging for troubleshooting SSH connection issues
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s | %(levelname)s | %(name)s | %(message)s')
    logging.getLogger('paramiko').setLevel(logging.DEBUG)
    logging.getLogger('sshtunnel').setLevel(logging.DEBUG)

    print("Setting up SSH tunnel to PythonAnywhere...")
    # Increase timeouts slightly to be robust on slow connections
    tunnel: SSHTunnelForwarder
    with SSHTunnelForwarder(
        (SSH_HOST, SSH_PORT),
        ssh_username=SSH_USERNAME,
        ssh_password=SSH_PASSWORD,
        ssh_pkey=SSH_PKEY,
        ssh_private_key_password=SSH_PKEY_PASSPHRASE,
        remote_bind_address=(DB_REMOTE_HOST, DB_REMOTE_PORT),
        allow_agent=False,
        mute_exceptions=False,
        set_keepalive=5.0,
    ) as tunnel:
        local_port = tunnel.local_bind_port
        print(f"SSH tunnel established. Local forwarded port: {local_port}")
        print("Connecting to MySQL through the tunnel...")

        conn = None
        cursor = None
        try:
            conn = mysql.connector.connect(
                user=DB_USER,
                password=DB_PASSWORD,
                host="127.0.0.1",
                port=local_port,
                database=DB_NAME,
                connection_timeout=10,
            )
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            cursor.execute("SELECT DATABASE()")
            db_result = cursor.fetchone()
            print(f"Connection success. SELECT 1 => {result}, DATABASE() => {db_result}")
            return 0
        except mysql.connector.Error as err:
            print(f"MySQL error: {err}")
            return 2
        except Exception as e:
            print(f"Unexpected error: {e}")
            return 3
        finally:
            try:
                if cursor is not None:
                    cursor.close()
            except Exception:
                pass
            try:
                if conn is not None and conn.is_connected():
                    conn.close()
            except Exception:
                pass
            print("Closed MySQL connection. Tearing down SSH tunnel...")
    print("SSH tunnel closed.")
    return 0


if __name__ == "__main__":
    sys.exit(test_connection())
