"""
Example: Connect to a remote MySQL database on PythonAnywhere via SSH tunnel.

Prerequisites:
  pip install sshtunnel mysqlclient

Required environment variables (PowerShell examples):
  $env:CG_SSH_HOST='yourusername.pythonanywhere.com'
  $env:CG_SSH_USER='yourusername'
  $env:CG_SSH_PASSWORD='your_pythonanywhere_web_password'
  $env:CG_REMOTE_DB_HOST='yourusername.mysql.pythonanywhere-services.com'
  $env:CG_DB_USER='yourusername'
  $env:CG_DB_PASSWORD='your_database_password'
  $env:CG_DB_NAME='yourusername$mydatabase'

Run:
  python projects\country_game\examples\pythonanywhere_tunnel_example.py
"""
import os

import sshtunnel
import MySQLdb

# Set global timeouts per guidance
sshtunnel.SSH_TIMEOUT = 10.0
sshtunnel.TUNNEL_TIMEOUT = 10.0


def main():
    ssh_host = os.getenv('CG_SSH_HOST')
    ssh_user = os.getenv('CG_SSH_USER')
    ssh_password = os.getenv('CG_SSH_PASSWORD')
    remote_db_host = os.getenv('CG_REMOTE_DB_HOST')
    remote_db_port = int(os.getenv('CG_REMOTE_DB_PORT', '3306'))

    db_user = os.getenv('CG_DB_USER')
    db_password = os.getenv('CG_DB_PASSWORD')
    db_name = os.getenv('CG_DB_NAME')

    missing = [n for n, v in [
        ('CG_SSH_HOST', ssh_host),
        ('CG_SSH_USER', ssh_user),
        ('CG_SSH_PASSWORD', ssh_password),
        ('CG_REMOTE_DB_HOST', remote_db_host),
        ('CG_DB_USER', db_user),
        ('CG_DB_PASSWORD', db_password),
        ('CG_DB_NAME', db_name),
    ] if not v]
    if missing:
        print('Missing required environment variables: ' + ', '.join(missing))
        return

    with sshtunnel.SSHTunnelForwarder(
        (ssh_host, 22),
        ssh_username=ssh_user,
        ssh_password=ssh_password,
        remote_bind_address=(remote_db_host, remote_db_port),
    ) as tunnel:
        # Connect to MySQL through the local end of the tunnel
        connection = MySQLdb.connect(
            user=db_user,
            passwd=db_password,
            host='127.0.0.1',
            port=tunnel.local_bind_port,
            db=db_name,
            connect_timeout=10,
        )
        try:
            cursor = connection.cursor()
            cursor.execute('SELECT 1')
            print('Test query result:', cursor.fetchone())
        finally:
            connection.close()
            print('Connection closed')


if __name__ == '__main__':
    main()
