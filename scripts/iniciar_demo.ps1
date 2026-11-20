# Levanta el backend (Django) y el frontend (Vite) para la demostración, cada
# uno en su propia ventana de PowerShell. Uso, desde la raíz del proyecto:
#
#   powershell -ExecutionPolicy Bypass -File scripts\iniciar_demo.ps1
#   powershell -ExecutionPolicy Bypass -File scripts\iniciar_demo.ps1 -RedLocal
#   powershell -ExecutionPolicy Bypass -File scripts\iniciar_demo.ps1 -RedLocal -BackendEnRed
#
# Antes de arrancar detiene cualquier proceso que escuche en los puertos 8000
# y del frontend (5174), para no quedar con dos servidores a la vez.
#
# -RedLocal: la plataforma se abre también desde otros equipos de la misma red
#   (p. ej. el celular, para el enlace de restablecimiento de contraseña).
#   Vite escucha en 0.0.0.0 y el backend recibe IP_RED_LOCAL y FRONTEND_URL
#   con la IP de esta laptop (ALLOWED_HOSTS, CORS, CSRF y el enlace del correo).
#   El backend sigue en 127.0.0.1: el celular solo habla con Vite, que reenvía
#   /api al backend. Solo hace falta abrir el puerto del frontend en el firewall.
# -BackendEnRed: además, Django escucha en 0.0.0.0:8000 (no es necesario para
#   usar la plataforma; solo si quiere llamar a la API directamente).
# -Ip: fija la IP si la detección automática elige otra interfaz.
#
# Requisitos: backend\venv con las dependencias, backend\.env configurado,
# PostgreSQL encendido y "npm ci" ejecutado en frontend.
#
# Perfiles simultáneos: el token de sesión se guarda en el navegador, así que
# una misma ventana no admite dos sesiones. Abra cada perfil en una ventana
# distinta: una ventana normal, una de incógnito y otro navegador.

param(
    [int]$PuertoFrontend = 5174,
    [switch]$RedLocal,
    [switch]$BackendEnRed,
    [string]$Ip = ""
)

$ErrorActionPreference = "Stop"
$raiz = Split-Path -Parent $PSScriptRoot
$backend = Join-Path $raiz "backend"
$frontend = Join-Path $raiz "frontend"
$python = Join-Path $backend "venv\Scripts\python.exe"
$PuertoBackend = 8000

if (-not (Test-Path $python)) { throw "No se encontró $python. Cree el entorno virtual en backend\venv." }
if (-not (Test-Path (Join-Path $backend ".env"))) { throw "Falta backend\.env (copie backend\.env.example)." }
if (-not (Test-Path (Join-Path $frontend "node_modules"))) { throw "Ejecute 'npm ci' en la carpeta frontend." }

function Detener-Puerto([int]$puerto) {
    $pids = @(Get-NetTCPConnection -LocalPort $puerto -State Listen -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty OwningProcess -Unique | Where-Object { $_ -gt 0 })
    foreach ($id in $pids) {
        $proceso = Get-CimInstance Win32_Process -Filter "ProcessId=$id" -ErrorAction SilentlyContinue
        if (-not $proceso) { continue }
        Write-Host "Deteniendo $($proceso.Name) (PID $id) que escucha en el puerto $puerto."
        # El python.exe del venv es un lanzador: se detiene también su padre si
        # es el mismo programa, para que no vuelva a quedar un servidor colgado.
        $padre = Get-CimInstance Win32_Process -Filter "ProcessId=$($proceso.ParentProcessId)" -ErrorAction SilentlyContinue
        Stop-Process -Id $id -Force -ErrorAction SilentlyContinue
        if ($padre -and $padre.Name -eq $proceso.Name -and $padre.CommandLine -match "runserver") {
            Stop-Process -Id $padre.ProcessId -Force -ErrorAction SilentlyContinue
        }
    }
    for ($i = 0; $i -lt 10; $i++) {
        if (-not (Get-NetTCPConnection -LocalPort $puerto -State Listen -ErrorAction SilentlyContinue)) { return }
        Start-Sleep -Milliseconds 500
    }
    throw "El puerto $puerto sigue ocupado. Ciérrelo a mano y vuelva a intentarlo."
}

function Ip-Local {
    $config = Get-NetIPConfiguration | Where-Object { $_.IPv4DefaultGateway -and $_.NetAdapter.Status -eq "Up" } |
        Select-Object -First 1
    if (-not $config) { throw "No se encontró una red con puerta de enlace. Conéctese a la Wi-Fi o use -Ip." }
    return ($config.IPv4Address | Select-Object -First 1).IPAddress
}

Detener-Puerto $PuertoBackend
Detener-Puerto $PuertoFrontend

# Aplica migraciones pendientes antes de arrancar.
& $python (Join-Path $backend "manage.py") migrate --noinput
if ($LASTEXITCODE -ne 0) { throw "Falló 'manage.py migrate'. ¿Está encendido PostgreSQL?" }

$hostBackend = "127.0.0.1"
$hostFrontend = "localhost"
$entorno = ""
if ($RedLocal) {
    if (-not $Ip) { $Ip = Ip-Local }
    $hostFrontend = "0.0.0.0"
    if ($BackendEnRed) { $hostBackend = "0.0.0.0" }
    # Variables solo para la ventana del backend (tienen prioridad sobre el .env).
    $entorno = "`$env:IP_RED_LOCAL = '$Ip'; `$env:PUERTO_FRONTEND = '$PuertoFrontend'; " +
               "`$env:FRONTEND_URL = 'http://${Ip}:$PuertoFrontend'; "
    $perfil = (Get-NetConnectionProfile | Where-Object { $_.IPv4Connectivity -ne "Disconnected" } |
        Select-Object -First 1).NetworkCategory
    if ($perfil -ne "Private") {
        Write-Warning "La red actual no es 'Privada' ($perfil). Las reglas del firewall solo para la red privada no se aplicarán."
    }
}

Start-Process powershell -WorkingDirectory $backend -ArgumentList @(
    "-NoExit", "-Command",
    "`$Host.UI.RawUI.WindowTitle = 'Backend (Django)'; $entorno& '$python' manage.py runserver ${hostBackend}:$PuertoBackend --noreload"
)
Start-Process powershell -WorkingDirectory $frontend -ArgumentList @(
    "-NoExit", "-Command",
    "`$Host.UI.RawUI.WindowTitle = 'Frontend (Vite)'; npx vite --port $PuertoFrontend --host $hostFrontend --strictPort"
)

# Espera a que el frontend responda y abre el navegador.
$url = "http://localhost:$PuertoFrontend/"
for ($i = 0; $i -lt 30; $i++) {
    try { Invoke-WebRequest $url -UseBasicParsing -TimeoutSec 2 | Out-Null; break } catch { Start-Sleep -Seconds 1 }
}
Start-Process $url

Write-Host ""
Write-Host "Plataforma en $url (backend en http://${hostBackend}:$PuertoBackend)."
if ($RedLocal) {
    Write-Host "Desde el celular (misma Wi-Fi): http://${Ip}:$PuertoFrontend/"
    Write-Host "Los enlaces de restablecimiento de contraseña apuntan a http://${Ip}:$PuertoFrontend/restablecer/..."
    Write-Host "Si el celular no carga la página, abra el puerto $PuertoFrontend en el Firewall de Windows (red privada)."
}
Write-Host "Para probar los tres perfiles a la vez, abra cada uno en una ventana distinta:"
Write-Host "  - Administrador: ventana normal del navegador"
Write-Host "  - Líder técnico: ventana de incógnito"
Write-Host "  - Desarrollador: otro navegador"
Write-Host "Para detener la plataforma, cierre las dos ventanas de PowerShell."
