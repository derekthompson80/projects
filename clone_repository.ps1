# Script to clone the specified Git repository
# This script will first ensure Git is in the PATH and then clone the repository

# First, ensure Git is in the PATH by running the add_git_to_path script
Write-Host "Ensuring Git is in PATH..." -ForegroundColor Cyan
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$gitPathScript = Join-Path -Path $scriptPath -ChildPath "add_git_to_path.ps1"

if (Test-Path $gitPathScript) {
    try {
        & $gitPathScript
        if ($LASTEXITCODE -ne 0) {
            Write-Host "Failed to add Git to PATH. Please ensure Git is installed and try again." -ForegroundColor Red
            exit 1
        }

        # Refresh the PATH environment variable in the current session after running the script
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
        Write-Host "Refreshed PATH environment variable in current session." -ForegroundColor Cyan
    } catch {
        Write-Host "Error running add_git_to_path.ps1: $_" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "Could not find add_git_to_path.ps1 script at: $gitPathScript" -ForegroundColor Red
    exit 1
}

# Function to check if Git is available
function Test-GitAvailable {
    $gitCommand = Get-Command git -ErrorAction SilentlyContinue
    return $null -ne $gitCommand
}

# Verify Git is now available
if (-not (Test-GitAvailable)) {
    Write-Host "Git is still not available in PATH. Please ensure Git is installed correctly." -ForegroundColor Red
    exit 1
}

# Clone the repository
$repoUrl = "git@github.com:derekthompson80/projects.git"
$cloneDir = "projects"

Write-Host "Cloning repository: $repoUrl" -ForegroundColor Cyan

try {
    # Check if the directory already exists
    if (Test-Path $cloneDir) {
        Write-Host "Directory '$cloneDir' already exists. Please remove or rename it before cloning." -ForegroundColor Yellow
        exit 1
    }

    # Clone the repository
    git clone $repoUrl $cloneDir

    if ($LASTEXITCODE -eq 0) {
        Write-Host "Repository cloned successfully to: $(Resolve-Path $cloneDir)" -ForegroundColor Green
    } else {
        Write-Host "Failed to clone repository. Git returned exit code: $LASTEXITCODE" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "Error cloning repository: $_" -ForegroundColor Red
    exit 1
}

Write-Host "Clone operation completed." -ForegroundColor Green
