Remote MySQL connection via SSH tunnel (PythonAnywhere)

This project can connect to a remote MySQL database hosted on PythonAnywhere using an SSH tunnel.

Install dependencies (locally):
- pip install sshtunnel
- Option A (use MySQLdb, as in PythonAnywhere docs): pip install mysqlclient
- Option B (use mysql.connector via our helper): pip install mysql-connector-python

Environment variables (PowerShell examples):
  $env:CG_SSH_HOST='yourusername.pythonanywhere.com'
  $env:CG_SSH_USER='yourusername'
  $env:CG_SSH_PASSWORD='your_pythonanywhere_web_password'
  $env:CG_REMOTE_DB_HOST='yourusername.mysql.pythonanywhere-services.com'
  $env:CG_REMOTE_DB_PORT='3306'
  $env:CG_DB_USER='yourusername'
  $env:CG_DB_PASSWORD='your_database_password'
  $env:CG_DB_NAME='yourusername$mydatabase'

Option A: Use MySQLdb with the provided example
  python projects\country_game\examples\pythonanywhere_tunnel_example.py

Option B: Use mysql.connector via helper in code
Python snippet:
  from projects.country_game.ssh_db_tunnel import get_connector_connection_via_tunnel
  import os
  conn, close_func = get_connector_connection_via_tunnel(
      db_user=os.getenv('CG_DB_USER'),
      db_password=os.getenv('CG_DB_PASSWORD'),
      db_name=os.getenv('CG_DB_NAME'),
  )
  try:
      cur = conn.cursor()
      cur.execute('SELECT 1')
      print(cur.fetchone())
  finally:
      close_func()

Notes:
- The Flask app and scripts now honor CG_USE_SSH_TUNNEL. When set to true, connections go through the SSH tunnel; otherwise they connect directly using mysql.connector.
- Never commit real credentials. Prefer environment variables.
