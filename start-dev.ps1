# LocalMeshAI — one-command dev launcher (Windows PowerShell)
#
# Starts the FastAPI backend (uvicorn) and the Vite frontend together, each in its own
# window. Run from the repo root:
#
#     ./start-dev.ps1
#
# First run will create the backend venv and install deps if missing.

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot

$backend = Join-Path $root "backend"
$frontend = Join-Path $root "frontend"
$venv = Join-Path $backend ".venv"
$venvPython = Join-Path $venv "Scripts\python.exe"

Write-Host "LocalMeshAI dev launcher" -ForegroundColor Cyan

# --- Backend setup ---
if (-not (Test-Path $venvPython)) {
    Write-Host "Creating backend virtual environment..." -ForegroundColor Yellow
    python -m venv $venv
    & $venvPython -m pip install --upgrade pip
    & $venvPython -m pip install -r (Join-Path $backend "requirements.txt")
}

# --- Frontend setup ---
if (-not (Test-Path (Join-Path $frontend "node_modules"))) {
    Write-Host "Installing frontend dependencies..." -ForegroundColor Yellow
    Push-Location $frontend
    npm install
    Pop-Location
}

Write-Host "Launching backend on http://localhost:8000 ..." -ForegroundColor Green
Start-Process powershell -ArgumentList @(
    "-NoExit", "-Command",
    "Set-Location '$backend'; & '$venvPython' -m uvicorn main:app --reload --port 8000"
)

Write-Host "Launching frontend on http://localhost:5173 ..." -ForegroundColor Green
Start-Process powershell -ArgumentList @(
    "-NoExit", "-Command",
    "Set-Location '$frontend'; npm run dev"
)

Write-Host ""
Write-Host "Backend:  http://localhost:8000  (API docs at /docs)" -ForegroundColor Cyan
Write-Host "Frontend: http://localhost:5173" -ForegroundColor Cyan
Write-Host "Close the two spawned windows to stop the servers." -ForegroundColor DarkGray
