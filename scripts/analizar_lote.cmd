@echo off
rem Pasada del analisis en lote (validacion prospectiva del modelo activo).
rem La lanza oculta analizar_lote_oculto.vbs desde el Programador de tareas
rem (tarea "tesis\analizar_lote", cada 4 h). Tambien se puede ejecutar a mano.
rem Log diario en logs\lote_AAAAMMDD.log (se anade cada pasada).
setlocal
set "RAIZ=%~dp0.."
for /f %%d in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd"') do set "HOY=%%d"
if not exist "%RAIZ%\logs" mkdir "%RAIZ%\logs"
set "LOG=%RAIZ%\logs\lote_%HOY%.log"
set PYTHONIOENCODING=utf-8
cd /d "%RAIZ%\backend"
"%RAIZ%\backend\venv\Scripts\python.exe" -u -W ignore manage.py analizar_lote --usuario analisis_lote --max-llamadas 1500 >> "%LOG%" 2>&1
set "CODIGO=%ERRORLEVEL%"
for /f "delims=" %%t in ('powershell -NoProfile -Command "Get-Date -Format 'yyyy-MM-dd HH:mm:ss'"') do set "FIN=%%t"
echo === Codigo de salida %CODIGO% (%FIN%)>> "%LOG%"
echo.>> "%LOG%"
exit /b %CODIGO%
