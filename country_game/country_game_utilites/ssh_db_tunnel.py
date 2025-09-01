import MySQLdb
import sshtunnel

sshtunnel.SSH_TIMEOUT = 10.0
sshtunnel.TUNNEL_TIMEOUT = 10.0

with sshtunnel.SSHTunnelForwarder(
    ('ssh.pythonanywhere.com'),
    ssh_username='spade605', ssh_password='Beholder20!',
    remote_bind_address=('spade605.mysql.pythonanywhere-services.com', 3306),
    allow_agent=False,
    look_for_keys=False
) as tunnel:
    connection = MySQLdb.connect(
        user='spade605',
        passwd='Darklove90!',
        host='127.0.0.1', port=tunnel.local_bind_port,
        db='spade605$county_game_server',
    )
    # Do stuff
    connection.close()