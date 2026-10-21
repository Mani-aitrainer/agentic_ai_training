# setup-specify.ps1
# One-time setup for the Spec-Driven Development (SDD) session.
# It installs uv, installs the Spec Kit CLI ("specify"), adds both to your
# user PATH, and saves your OpenAI API key as a user environment variable.
#
# Run it from PowerShell (no admin needed):
#   powershell -ExecutionPolicy Bypass -File .\setup-specify.ps1
#
# After it finishes, CLOSE and REOPEN your terminal / VS Code so the new
# PATH and environment variables are picked up.

$ErrorActionPreference = "Stop"

Write-Host "`n[1/6] Checking Python and Git..." -ForegroundColor Cyan
try { python --version } catch { Write-Host "Python not found. Install Python 3.11+ from https://www.python.org/downloads/ and tick 'Add to PATH'." -ForegroundColor Red; exit 1 }
try { git --version }    catch { Write-Host "Git not found. Install it from https://git-scm.com/download/win" -ForegroundColor Yellow }

Write-Host "`n[2/6] Allowing local PowerShell scripts for your user (Spec Kit uses .ps1 scripts)..." -ForegroundColor Cyan
# When this script runs with "-ExecutionPolicy Bypass", PowerShell warns that the
# CurrentUser setting is "overridden". The setting is still saved, so we ignore that warning.
try {
    Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned -Force -ErrorAction Stop
} catch [System.Security.SecurityException] {
    Write-Host "Saved for CurrentUser (this window keeps Bypass). This is fine." -ForegroundColor Yellow
}
Get-ExecutionPolicy -List

Write-Host "`n[3/6] Installing uv (Python tool manager)..." -ForegroundColor Cyan
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
} else {
    Write-Host "uv is already installed."
}

Write-Host "`n[4/6] Adding $env:USERPROFILE\.local\bin to your user PATH..." -ForegroundColor Cyan
$bin = "$env:USERPROFILE\.local\bin"
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($userPath -notlike "*$bin*") {
    [Environment]::SetEnvironmentVariable("Path", "$userPath;$bin", "User")
    Write-Host "Added to user PATH."
} else {
    Write-Host "Already in user PATH."
}
$env:Path = "$env:Path;$bin"   # also use it in this window right now

Write-Host "`n[5/6] Installing the Spec Kit CLI (specify)..." -ForegroundColor Cyan
uv tool install specify-cli --force
uv tool update-shell
specify version

Write-Host "`n[6/6] Saving your OpenAI API key as a user environment variable..." -ForegroundColor Cyan
if ([Environment]::GetEnvironmentVariable("OPENAI_API_KEY", "User")) {
    Write-Host "OPENAI_API_KEY is already set. Skipping."
} else {
    $key = Read-Host "Paste your OpenAI API key (starts with sk-), or press Enter to skip"
    if ($key) {
        [Environment]::SetEnvironmentVariable("OPENAI_API_KEY", $key, "User")
        $env:OPENAI_API_KEY = $key
        Write-Host "Saved."
    } else {
        Write-Host "Skipped. Set it later with:  [Environment]::SetEnvironmentVariable('OPENAI_API_KEY','sk-...','User')"
    }
}

Write-Host "`nDone. Close and reopen your terminal, then run:  specify check" -ForegroundColor Green
