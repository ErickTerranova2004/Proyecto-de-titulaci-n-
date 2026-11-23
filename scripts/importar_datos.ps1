# Restaura en este equipo un respaldo creado con scripts\exportar_datos.ps1.
# Uso, desde la raíz del proyecto:
#
#   powershell -ExecutionPolicy Bypass -File scripts\importar_datos.ps1 -Respaldo C:\ruta\riesgo_despliegue_AAAAMMDD_HHMMSS_exportado.dump
#   powershell -ExecutionPolicy Bypass -File scripts\importar_datos.ps1 -Respaldo <ruta> -Reemplazar
#
# Pasos:
#   1. Lee la conexión de backend\.env (POSTGRES_DB, POSTGRES_USER,
#      POSTGRES_PASSWORD, POSTGRES_HOST, POSTGRES_PORT) sin mostrarla.
#   2. Crea la base si no existe. Si existe y ya tiene tablas, se detiene,
#      salvo con -Reemplazar: entonces primero la respalda (pg_dump, carpeta
#      tesis_respaldos junto al repositorio), luego la borra y la vuelve a crear.
#   3. pg_restore del respaldo (sin dueños ni permisos del equipo de origen:
#      todo queda a nombre de POSTGRES_USER).
#   4. manage.py migrate (aplica las migraciones que el respaldo no tenga).
#
# -Base: restaura en otra base en lugar de POSTGRES_DB (p. ej. para ensayar).
#
# Requisitos: PostgreSQL 16 encendido, backend\venv con las dependencias y
# backend\.env con su propia contraseña de PostgreSQL.

param(
    [Parameter(Mandatory = $true)][string]$Respaldo,
    [switch]$Reemplazar,
    [string]$Base = ""
)

$ErrorActionPreference = "Stop"
$raiz = Split-Path -Parent $PSScriptRoot
$backend = Join-Path $raiz "backend"
$archivoEnv = Join-Path $backend ".env"
$python = Join-Path $backend "venv\Scripts\python.exe"
if (-not (Test-Path $archivoEnv)) { throw "Falta backend\.env (copie backend\.env.example y complételo)." }
if (-not (Test-Path $python)) { throw "No se encontró $python. Cree el entorno virtual en backend\venv." }
if (-not (Test-Path -LiteralPath $Respaldo)) { throw "No existe el respaldo $Respaldo." }
$Respaldo = (Resolve-Path -LiteralPath $Respaldo).Path

function Leer-Env([string]$ruta) {
    $valores = @{}
    foreach ($linea in Get-Content -LiteralPath $ruta -Encoding UTF8) {
        $l = $linea.Trim()
        if (-not $l -or $l.StartsWith("#") -or -not $l.Contains("=")) { continue }
        $i = $l.IndexOf("=")
        $valores[$l.Substring(0, $i).Trim()] = $l.Substring($i + 1).Trim().Trim('"').Trim("'")
    }
    return $valores
}

function Buscar-Programa([string]$nombre) {
    $cmd = Get-Command $nombre -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    $candidato = Get-ChildItem "C:\Program Files\PostgreSQL\*\bin\$nombre.exe" -ErrorAction SilentlyContinue |
        Sort-Object FullName -Descending | Select-Object -First 1
    if ($candidato) { return $candidato.FullName }
    throw "No se encontró $nombre. Instale PostgreSQL 16 o añada su carpeta bin al PATH."
}

$env_ = Leer-Env $archivoEnv
if (-not $Base) { $Base = $env_["POSTGRES_DB"] }
if (-not $Base) { throw "POSTGRES_DB no está definido en backend\.env." }
if ($Base -notmatch "^[A-Za-z_][A-Za-z0-9_]*$") { throw "Nombre de base no válido: $Base" }
$usuario = if ($env_["POSTGRES_USER"]) { $env_["POSTGRES_USER"] } else { "postgres" }
$servidor = if ($env_["POSTGRES_HOST"]) { $env_["POSTGRES_HOST"] } else { "localhost" }
$puerto = if ($env_["POSTGRES_PORT"]) { $env_["POSTGRES_PORT"] } else { "5432" }
$conexion = @("-h", $servidor, "-p", $puerto, "-U", $usuario)

$psql = Buscar-Programa "psql"
$pgRestore = Buscar-Programa "pg_restore"

$env:PGPASSWORD = $env_["POSTGRES_PASSWORD"]
try {
    # El respaldo se puede leer.
    & $pgRestore -l $Respaldo | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "$Respaldo no es un respaldo válido de pg_dump (-Fc)." }

    $existe = (& $psql @conexion -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname = '$Base'")
    if ($LASTEXITCODE -ne 0) { throw "No se pudo conectar a PostgreSQL. ¿Está encendido? ¿Es correcta la contraseña de backend\.env?" }

    if ("$existe".Trim() -eq "1") {
        $tablas = (& $psql @conexion -d $Base -tAc "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public'")
        if ([int]"$tablas".Trim() -gt 0) {
            if (-not $Reemplazar) {
                throw ("La base $Base ya existe y tiene $("$tablas".Trim()) tablas. Para sustituirla por el respaldo, " +
                       "vuelva a ejecutar con -Reemplazar (antes se respalda la base actual).")
            }
            $carpeta = Join-Path (Split-Path -Parent $raiz) "tesis_respaldos"
            New-Item -ItemType Directory -Force -Path $carpeta | Out-Null
            $previo = Join-Path $carpeta ("{0}_{1}_antes_importar.dump" -f $Base, (Get-Date -Format "yyyyMMdd_HHmmss"))
            Write-Host "Respaldando la base actual en $previo ..."
            & (Buscar-Programa "pg_dump") -Fc @conexion -d $Base -f $previo
            if ($LASTEXITCODE -ne 0) { throw "No se pudo respaldar la base actual; no se ha cambiado nada." }
        }
        Write-Host "Borrando la base $Base ..."
        & $psql @conexion -d postgres -v ON_ERROR_STOP=1 -qc "DROP DATABASE `"$Base`" WITH (FORCE)" | Out-Null
        if ($LASTEXITCODE -ne 0) { throw "No se pudo borrar la base $Base (¿hay un backend conectado?)." }
    }

    Write-Host "Creando la base $Base ..."
    & $psql @conexion -d postgres -v ON_ERROR_STOP=1 -qc "CREATE DATABASE `"$Base`" ENCODING 'UTF8' TEMPLATE template0" | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "No se pudo crear la base $Base." }

    Write-Host "Restaurando $Respaldo ..."
    & $pgRestore @conexion -d $Base --no-owner --no-privileges --exit-on-error $Respaldo
    if ($LASTEXITCODE -ne 0) { throw "pg_restore falló (código $LASTEXITCODE). Revise los mensajes anteriores." }
} finally {
    Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue
}

# Migraciones sobre la misma base (las variables del proceso tienen prioridad
# sobre backend\.env).
Write-Host "Aplicando migraciones ..."
$basePrevia = $env:POSTGRES_DB
$env:POSTGRES_DB = $Base
try {
    Push-Location $backend
    & $python manage.py migrate --noinput
    if ($LASTEXITCODE -ne 0) { throw "Falló 'manage.py migrate'." }
} finally {
    Pop-Location
    if ($null -eq $basePrevia) { Remove-Item Env:POSTGRES_DB -ErrorAction SilentlyContinue } else { $env:POSTGRES_DB = $basePrevia }
}

Write-Host ""
Write-Host "Listo: la base $Base tiene los datos del respaldo."
Write-Host "Las sesiones no se copian: inicie sesión de nuevo en la plataforma."
Write-Host "Arranque con: powershell -ExecutionPolicy Bypass -File scripts\iniciar_demo.ps1"
