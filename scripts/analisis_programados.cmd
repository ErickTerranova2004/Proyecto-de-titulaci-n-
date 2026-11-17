@echo off
rem Analisis interactivos reales repartidos en el tiempo (scripts\analisis_programados.py).
rem Uso: scripts\analisis_programados.cmd [--cantidad 40] [--hasta 11:00] [--usuario revision_dev]
rem Requiere el backend en marcha. Pide la contrasena del usuario al empezar.
setlocal
set "RAIZ=%~dp0.."
set PYTHONIOENCODING=utf-8
"%RAIZ%\backend\venv\Scripts\python.exe" -u "%RAIZ%\scripts\analisis_programados.py" %*
exit /b %ERRORLEVEL%
