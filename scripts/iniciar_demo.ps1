# Levanta el backend (Django) y el frontend (Vite) para la demostración, cada
# uno en su propia ventana de PowerShell. Uso, desde la raíz del proyecto:
#
#   powershell -ExecutionPolicy Bypass -File scripts\iniciar_demo.ps1
#
# Requisitos: backend\venv con las dependencias, backend\.env configurado,
# PostgreSQL encendido y "npm ci" ejecutado en frontend.
#
# Perfiles simultáneos: el token de sesión se guarda en el navegador, así que
# una misma ventana no admite dos sesiones. Abra cada perfil en una ventana
# distinta: una ventana normal, una de incógnito y otro navegador.

param(
    [int]$PuertoFrontend = 5174
)

$ErrorActionPreference = "Stop"
$raiz = Split-Path -Parent $PSScriptRoot
$backend = Join-Path $raiz "backend"
$frontend = Join-Path $raiz "frontend"
$python = Join-Path $backend "venv\Scripts\python.exe"

if (-not (Test-Path $python)) { throw "No se encontró $python. Cree el entorno virtual en backend\venv." }
if (-not (Test-Path (Join-Path $backend ".env"))) { throw "Falta backend\.env (copie backend\.env.example)." }
if (-not (Test-Path (Join-Path $frontend "node_modules"))) { throw "Ejecute 'npm ci' en la carpeta frontend." }

# Aplica migraciones pendientes antes de arrancar.
& $python (Join-Path $backend "manage.py") migrate --noinput
if ($LASTEXITCODE -ne 0) { throw "Falló 'manage.py migrate'. ¿Está encendido PostgreSQL?" }

Start-Process powershell -WorkingDirectory $backend -ArgumentList @(
    "-NoExit", "-Command", "`$Host.UI.RawUI.WindowTitle = 'Backend (Django)'; & '$python' manage.py runserver 127.0.0.1:8000"
)
Start-Process powershell -WorkingDirectory $frontend -ArgumentList @(
    "-NoExit", "-Command", "`$Host.UI.RawUI.WindowTitle = 'Frontend (Vite)'; npx vite --port $PuertoFrontend --host 0.0.0.0"
)

# Espera a que el frontend responda y abre el navegador.
$url = "http://localhost:$PuertoFrontend/"
for ($i = 0; $i -lt 30; $i++) {
    try { Invoke-WebRequest $url -UseBasicParsing -TimeoutSec 2 | Out-Null; break } catch { Start-Sleep -Seconds 1 }
}
Start-Process $url

Write-Host ""
Write-Host "Plataforma en $url (backend en http://127.0.0.1:8000)."
Write-Host "Si el puerto $PuertoFrontend está ocupado, Vite usa el siguiente libre: revise la ventana 'Frontend (Vite)'."
Write-Host "Para probar los tres perfiles a la vez, abra cada uno en una ventana distinta:"
Write-Host "  - Administrador: ventana normal del navegador"
Write-Host "  - Líder técnico: ventana de incógnito"
Write-Host "  - Desarrollador: otro navegador"
Write-Host "Para detener la plataforma, cierre las dos ventanas de PowerShell."
