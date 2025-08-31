import os
import sys

# Prefer loading .env if present
try:
    from dotenv import load_dotenv, find_dotenv  # type: ignore
    load_dotenv(find_dotenv(), override=False)
except Exception:
    pass

from projects.country_game.ssh_db_tunnel import quick_test_connection, get_connector_connection_via_tunnel


def print_env_summary():
    keys = [
        'CG_SSH_HOST', 'CG_SSH_USER', 'CG_SSH_PASSWORD',
        'CG_REMOTE_DB_HOST', 'CG_REMOTE_DB_PORT',
        'CG_DB_USER', 'CG_DB_PASSWORD', 'CG_DB_NAME'
    ]
    for k in keys:
        v = os.getenv(k)
        masked = ('<set>' if v else '<missing>')
        if k in ('CG_DB_NAME', 'CG_REMOTE_DB_HOST') and v:
            masked = v
        print(f"{k}: {masked}")


def main():
    # Provide sensible defaults based on the user's request if env not set
    os.environ.setdefault('CG_SSH_HOST', 'ssh.pythonanywhere.com')
    os.environ.setdefault('CG_SSH_USER', 'spade605')
    os.environ.setdefault('CG_SSH_PASSWORD', 'Darklove90!')
    os.environ.setdefault('CG_REMOTE_DB_HOST', 'spade605.mysql.pythonanywhere-services.com')
    os.environ.setdefault('CG_REMOTE_DB_PORT', '3306')
    os.environ.setdefault('CG_DB_USER', 'spade605')
    os.environ.setdefault('CG_DB_PASSWORD', 'Darklove90!')
    os.environ.setdefault('CG_DB_NAME', 'spade605$county_game_server')

    print("Attempting SSH tunnel connection to MySQL (PythonAnywhere)...")
    print_env_summary()

    try:
        conn, close_func = get_connector_connection_via_tunnel()
        try:
            cur = conn.cursor()
            cur.execute('SELECT DATABASE()')
            db_name = cur.fetchone()[0]
            cur.execute('SELECT 1')
            one = cur.fetchone()[0]
            print(f"Connected successfully. Current DB: {db_name!r}, SELECT 1 -> {one}")
        finally:
            close_func()
        print("Success: Tunnel established and query executed.")
        return 0
    except Exception as e:
        print("Failed to connect via SSH tunnel:", e)
        return 1


if __name__ == '__main__':
    sys.exit(main())
