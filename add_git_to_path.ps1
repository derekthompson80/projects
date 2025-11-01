# Script to add Git to the system PATH environment variable
# This script should be run with administrator privileges

# Function to check if Git is already in PATH
function Test-GitInPath {
    $gitCommand = Get-Command git -ErrorAction SilentlyContinue
    return $null -ne $gitCommand
}

# Function to find Git installation path
function Find-GitInstallPath {
    $defaultPath = "C:\Program Files\Git\cmd"
    if (Test-Path $defaultPath) {
        return $defaultPath
    }
    
    # Check other common locations
    $alternativePaths = @(
        "C:\Program Files (x86)\Git\cmd",
        "${env:ProgramFiles}\Git\cmd",
        "${env:ProgramFiles(x86)}\Git\cmd"
    )
    
    foreach ($path in $alternativePaths) {
        if (Test-Path $path) {
            return $path
        }
    }
    
    return $null
}

# Main script execution
Write-Host "Checking if Git is in PATH..." -ForegroundColor Cyan

if (Test-GitInPath) {
    Write-Host "Git is already in PATH. No changes needed." -ForegroundColor Green
    exit 0
}

Write-Host "Git is not in PATH. Attempting to find Git installation..." -ForegroundColor Yellow

$gitPath = Find-GitInstallPath
if ($null -eq $gitPath) {
    Write-Host "Could not find Git installation. Please install Git or manually add its path to PATH." -ForegroundColor Red
    exit 1
}

Write-Host "Found Git at: $gitPath" -ForegroundColor Cyan
Write-Host "Adding Git to system PATH..." -ForegroundColor Yellow

try {
    # Get the current PATH
    $currentPath = [Environment]::GetEnvironmentVariable("PATH", "Machine")
    
    # Check if the Git path is already in PATH (just to be extra safe)
    if ($currentPath -split ";" -contains $gitPath) {
        Write-Host "Git path is already in PATH. No changes needed." -ForegroundColor Green
        exit 0
    }
    
    # Add Git path to PATH
    $newPath = "$currentPath;$gitPath"
    [Environment]::SetEnvironmentVariable("PATH", $newPath, "Machine")
    
    Write-Host "Successfully added Git to system PATH." -ForegroundColor Green
    Write-Host "Please restart your command prompt or PowerShell to use Git." -ForegroundColor Cyan
    
    # Verify the change
    $updatedPath = [Environment]::GetEnvironmentVariable("PATH", "Machine")
    if ($updatedPath -split ";" -contains $gitPath) {
        Write-Host "Verification successful: Git path is now in system PATH." -ForegroundColor Green
    } else {
        Write-Host "Verification failed: Git path was not added to system PATH." -ForegroundColor Red
    }
} catch {
    Write-Host "Error adding Git to PATH: $_" -ForegroundColor Red
    Write-Host "You may need to run this script as Administrator." -ForegroundColor Yellow
    exit 1
}