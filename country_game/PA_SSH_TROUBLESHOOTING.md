PythonAnywhere SSH and MySQL tunneling troubleshooting

This project connects to a PythonAnywhere MySQL database via an SSH tunnel. If the tunnel fails to start or times out, follow this checklist adapted from https://help.pythonanywhere.com/pages/SSHAccess

Environment variables used
- CG_SSH_HOST: usually ssh.pythonanywhere.com
- CG_SSH_USER: your PythonAnywhere username (e.g. spade605)
- CG_SSH_PASSWORD: your PythonAnywhere web login password. If you use 2FA, create an app-specific password for SSH and use that here.
- CG_REMOTE_DB_HOST: yourusername.mysql.pythonanywhere-services.com
- CG_REMOTE_DB_PORT: 3306
- CG_DB_USER: your PythonAnywhere username (not root)
- CG_DB_PASSWORD: your MySQL password (set on PythonAnywhere)
- CG_DB_NAME: optional; if set, it’s typically yourusername$databasename
- CG_CONNECT_TIMEOUT_SECONDS: total timeout budget (default 30)

Checklist before connecting
1) Verify hosts
   - CG_SSH_HOST should be ssh.pythonanywhere.com
   - CG_REMOTE_DB_HOST should end with .mysql.pythonanywhere-services.com
   - It should usually start with your username: <username>.mysql.pythonanywhere-services.com

2) Verify users/passwords
   - CG_SSH_USER must be your PythonAnywhere username
   - If you have 2FA enabled, generate an “SSH” app-specific password on PythonAnywhere and use it for CG_SSH_PASSWORD
   - CG_DB_USER should be your PA username, not root or admin
   - CG_DB_PASSWORD is your MySQL password (not the SSH one)

3) Networking/permissions facts
   - You cannot connect directly to the MySQL host from the public internet; you must use an SSH tunnel via ssh.pythonanywhere.com
   - SSH port is 22

4) Common errors and hints
   - Could not open connection to gateway / Could not establish session to SSH gateway
     * Check CG_SSH_HOST and CG_SSH_USER
     * If 2FA is on, use an app-specific password
     * Ensure your local network allows outbound TCP 22
   - Authentication failed
     * Wrong CG_SSH_PASSWORD or wrong username
   - MySQL access denied
     * Re-check CG_DB_USER/CG_DB_PASSWORD; ensure the DB user exists and has rights

How to run the connection test
- PowerShell example from project root:
  $env:PYTHONPATH = "C:\Users\spade\PyCharmMiscProject"
  python projects\country_game\confirm_remote_db_connection.py

The script will log each step and time out after 30 seconds by default.


Direct SSH login (interactive)
- From PowerShell, you can open a shell session to your PythonAnywhere account with:
  ssh spade605@ssh.pythonanywhere.com
- When prompted, type the password: Beholder30!
  (If 2FA is enabled, use your PythonAnywhere app-specific SSH password instead.)
- You can also run the helper script in this project:
  projects\country_game\ssh_login.ps1
