"""
Confirm connection to PythonAnywhere MySQL via SSH tunnel using provided credentials.

Run:
  python projects\country_game\examples\confirm_remote_db_connection.py

This uses:
  SSH host: ssh.pythonanywhere.com
  SSH user: spade605
  SSH password: Darklove90!
  Remote DB host: spade605.mysql.pythonanywhere-services.com
  DB user: spade605
  DB password: Darklove90!
  DB name: spade605$county_game_server

Requires packages:
  pip install sshtunnel mysqlclient
"""
import sshtunnel
import mysql.connector

sshtunnel.SSH_TIMEOUT = 10.0
sshtunnel.TUNNEL_TIMEOUT = 10.0

SSH_HOST = 'ssh.pythonanywhere.com'
SSH_USER = 'spade605'
SSH_PASSWORD = 'Darklove90!'
REMOTE_DB_HOST = 'spade605.mysql.pythonanywhere-services.com'
REMOTE_DB_PORT = 3306
DB_USER = 'spade605'
DB_PASSWORD = 'Darklove90!'
DB_NAME = 'spade605$county_game_server'


def main():
    print('Opening SSH tunnel to PythonAnywhere...')
    with sshtunnel.SSHTunnelForwarder(
        (SSH_HOST, 22),
        ssh_username=SSH_USER,
        ssh_password=SSH_PASSWORD,
        remote_bind_address=(REMOTE_DB_HOST, REMOTE_DB_PORT),
        allow_agent=False,
        look_for_keys=False,
    ) as tunnel:
        local_port = tunnel.local_bind_port
        print(f'Tunnel established. Local bind port: {local_port}')
        print('Connecting to MySQL through the tunnel...')
        conn = mysql.connector.connect(
            user=DB_USER,
            password=DB_PASSWORD,
            host='127.0.0.1',
            port=local_port,
            database=DB_NAME,
            connection_timeout=10,
        )
        try:
            cur = conn.cursor()
            cur.execute('SELECT 1')
            one = cur.fetchone()
            cur.execute('SELECT DATABASE()')
            dbname = cur.fetchone()
            print('SELECT 1 result:', one)
            print('Current database:', dbname)
            print('Connection confirmed.')
        finally:
            conn.close()
            print('MySQL connection closed. Tunnel will close now.')


if __name__ == '__main__':
    main()
