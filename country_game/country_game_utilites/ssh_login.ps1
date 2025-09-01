# Helper script to SSH into PythonAnywhere
# Usage:
#   Right-click -> Run with PowerShell (or run from a PowerShell prompt)
#
# It will run the command:
#   ssh spade605@ssh.pythonanywhere.com
# and you should type the password when prompted: Beholder30!
#
# Security note: Typing the password at the prompt is safer than embedding it in a command line.
# If you use 2FA on PythonAnywhere, use an app-specific SSH password.

Write-Host "Launching SSH session to PythonAnywhere..." -ForegroundColor Cyan
Write-Host "Command: ssh spade605@ssh.pythonanywhere.com" -ForegroundColor Yellow
Write-Host "When prompted for password, enter: Beholder30!" -ForegroundColor Yellow

# Execute the SSH command (interactive)
ssh spade605@ssh.pythonanywhere.com
