import unittest
from unittest.mock import patch, MagicMock

# Module under test
import projects.country_game.country_game_utilites.ssh_db_tunnel as ssh_db_tunnel


class TestSshDbTunnel(unittest.TestCase):
    @patch("projects.country_game.country_game_utilites.ssh_db_tunnel.MySQLdb")
    @patch("projects.country_game.country_game_utilites.ssh_db_tunnel.sshtunnel.SSHTunnelForwarder")
    def test_connect_via_tunnel_parameters(self, mock_tunnel_forwarder, mock_mysqldb):
        # Arrange: configure the SSHTunnelForwarder instance
        tunnel_instance = mock_tunnel_forwarder.return_value
        tunnel_instance.local_bind_port = 12345

        # Mock MySQLdb.connect to return a fake connection
        fake_conn = MagicMock(name="MySQLConnection")
        mock_mysqldb.connect.return_value = fake_conn

        # Act
        conn = ssh_db_tunnel.connect_via_tunnel()

        # Assert: ensure a connection object is returned
        self.assertIs(conn, fake_conn)

        # Assert: SSHTunnelForwarder called with expected parameters
        mock_tunnel_forwarder.assert_called_once()
        args, kwargs = mock_tunnel_forwarder.call_args
        # First positional arg should be SSH host string
        self.assertEqual(args[0], ssh_db_tunnel.SSH_HOST)
        # Keyword arguments
        self.assertEqual(kwargs.get("ssh_username"), ssh_db_tunnel.SSH_USERNAME)
        self.assertEqual(kwargs.get("ssh_password"), ssh_db_tunnel.SSH_PASSWORD)
        self.assertEqual(
            kwargs.get("remote_bind_address"),
            (ssh_db_tunnel.REMOTE_DB_HOST, ssh_db_tunnel.REMOTE_DB_PORT),
        )
        # Start should be called to activate the tunnel
        tunnel_instance.start.assert_called_once()
        # Keepalive is configured for tunnel stability
        self.assertEqual(kwargs.get("set_keepalive"), 15)

        # Assert: MySQLdb.connect called with expected parameters including DB name
        mock_mysqldb.connect.assert_called_once()
        _, db_kwargs = mock_mysqldb.connect.call_args
        self.assertEqual(db_kwargs.get("user"), ssh_db_tunnel.DB_USER)
        self.assertEqual(db_kwargs.get("passwd"), ssh_db_tunnel.DB_PASSWORD)
        self.assertEqual(db_kwargs.get("host"), "127.0.0.1")
        self.assertEqual(db_kwargs.get("port"), tunnel_instance.local_bind_port)
        self.assertEqual(db_kwargs.get("db"), "spade605$county_game_server")

        # The connection should expose the tunnel for debugging
        self.assertIs(getattr(conn, "_ssh_tunnel", None), tunnel_instance)
        
        # Closing the connection should stop the tunnel
        conn.close()
        tunnel_instance.stop.assert_called_once()

        # Auto-reconnect ping should be invoked
        fake_conn.ping.assert_called()


if __name__ == "__main__":
    unittest.main()
