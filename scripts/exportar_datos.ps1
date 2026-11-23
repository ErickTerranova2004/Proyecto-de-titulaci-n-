# Exporta la base de datos de la plataforma a un respaldo con fecha
# (pg_dump -Fc), FUERA del repositorio, para restaurarla en otro equipo con
# scripts\importar_datos.ps1. Uso, desde la raíz del proyecto:
#
#   powershell -ExecutionPolicy Bypass -File scripts\exportar_datos.ps1
#   powershell -ExecutionPolicy Bypass -File scripts\exportar_datos.ps1 -Destino D:\respaldos -Nota compartir
#
# - Lee POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_HOST y
#   POSTGRES_PORT de backend\.env sin mostrarlos. La contraseña solo vive en
#   la variable PGPASSWORD de este proceso y se borra al terminar.
# - Destino por defecto: la carpeta tesis_respaldos junto al repositorio.
#   Se niega a escribir dentro del repositorio.
# - No exporta el contenido de authtoken_token ni django_session (sesiones
#   abiertas): quien restaure inicia sesión de nuevo.
#
# El respaldo contiene datos de la plataforma (usuarios con sus correos y
# contraseñas cifradas, análisis, decisiones). Compártalo solo por un medio
# privado (unidad compartida con acceso restringido, memoria USB); NUNCA por
# GitHub ni otro sitio público.

param(
    [string]$Destino = "",
    [string]$Nota = "exportado"
)

$ErrorActionPreference = "Stop"
$raiz = Split-Path -Parent $PSScriptRoot
$archivoEnv = Join-Path $raiz "backend\.env"
if (-not (Test-Path $archivoEnv)) { throw "Falta backend\.env (copie backend\.env.example y complételo)." }

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
$base = $env_["POSTGRES_DB"]
if (-not $base) { throw "POSTGRES_DB no está definido en backend\.env." }
$usuario = if ($env_["POSTGRES_USER"]) { $env_["POSTGRES_USER"] } else { "postgres" }
$servidor = if ($env_["POSTGRES_HOST"]) { $env_["POSTGRES_HOST"] } else { "localhost" }
$puerto = if ($env_["POSTGRES_PORT"]) { $env_["POSTGRES_PORT"] } else { "5432" }

if (-not $Destino) { $Destino = Join-Path (Split-Path -Parent $raiz) "tesis_respaldos" }
New-Item -ItemType Directory -Force -Path $Destino | Out-Null
$destinoAbs = (Resolve-Path -LiteralPath $Destino).Path.TrimEnd("\")
$raizAbs = (Resolve-Path -LiteralPath $raiz).Path.TrimEnd("\")
if ($destinoAbs -eq $raizAbs -or $destinoAbs.StartsWith($raizAbs + "\", [StringComparison]::OrdinalIgnoreCase)) {
    throw "El destino está dentro del repositorio ($destinoAbs). Elija una carpeta fuera de él."
}

$nota = ($Nota -replace "[^A-Za-z0-9_-]", "_")
$archivo = Join-Path $destinoAbs ("{0}_{1}_{2}.dump" -f $base, (Get-Date -Format "yyyyMMdd_HHmmss"), $nota)
$pgDump = Buscar-Programa "pg_dump"

$env:PGPASSWORD = $env_["POSTGRES_PASSWORD"]
try {
    & $pgDump -Fc -h $servidor -p $puerto -U $usuario -d $base `
        --exclude-table-data=authtoken_token --exclude-table-data=django_session -f $archivo
    if ($LASTEXITCODE -ne 0) { throw "pg_dump terminó con código $LASTEXITCODE. ¿Está encendido PostgreSQL?" }
} finally {
    Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue
}

# Comprobación: el respaldo se puede leer y tiene tablas.
$pgRestore = Buscar-Programa "pg_restore"
$tablas = @(& $pgRestore -l $archivo | Select-String " TABLE DATA ").Count
if ($LASTEXITCODE -ne 0 -or $tablas -eq 0) { throw "El respaldo $archivo no se pudo verificar." }

$tamano = [math]::Round((Get-Item $archivo).Length / 1MB, 1)
Write-Host ""
Write-Host "Respaldo creado: $archivo ($tamano MB, $tablas tablas con datos)."
Write-Host "Compártalo solo por un medio privado. NUNCA lo suba a GitHub."
Write-Host "Para restaurarlo en otro equipo: scripts\importar_datos.ps1 -Respaldo <ruta del .dump>"
