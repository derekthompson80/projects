import paramiko
import MySQLdb
import sshtunnel

# Workaround for Paramiko v3+ removal of DSSKey which sshtunnel may try to access
if not hasattr(paramiko, "DSSKey"):
    try:
        paramiko.DSSKey = paramiko.RSAKey  # type: ignore[attr-defined]
    except Exception:
        pass

sshtunnel.SSH_TIMEOUT = 10.0
sshtunnel.TUNNEL_TIMEOUT = 10.0

with sshtunnel.SSHTunnelForwarder(
    ('ssh.pythonanywhere.com'),
    ssh_username='spade605',
    ssh_password='Beholder20!',
    remote_bind_address=('spade605.mysql.pythonanywhere-services.com', 3306),
    allow_agent=False,
    host_pkey_directories=[],
    set_keepalive=15,
) as tunnel:
    connection = MySQLdb.connect(
        user='spade605',
        passwd='Darklove90!',
        host='127.0.0.1',
        port=tunnel.local_bind_port,
        db='spade605$blog',
        connect_timeout=10,
        charset='utf8mb4',
        use_unicode=True,
    )
    try:
        # Do stuff
        pass
    finally:
        connection.close()