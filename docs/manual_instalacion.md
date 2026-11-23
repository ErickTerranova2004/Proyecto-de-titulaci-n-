# Manual de instalación (otra persona, otro equipo con Windows)

Este manual explica cómo poner en marcha la plataforma en un equipo nuevo, con
una copia de los datos de la tesis. Está pensado para Windows 10/11 con
PowerShell y VS Code.

## 1. Qué trae el repositorio y qué no

| Archivo o carpeta | ¿En GitHub? | Qué hacer |
|---|---|---|
| Código (`backend/`, `frontend/`, `scripts/`, scripts `*.py` de la raíz) | Sí | Se clona |
| Modelos `modelos/modelo_riesgo_v2*` (Random Forest), `_v2_xgb*` (XGBoost) y los retirados `_v1*`, `_v1_1*` (`.joblib` y `.json`) | Sí | Se clona. La base guarda solo el nombre del archivo y la plataforma lo busca en `modelos/` |
| Datasets `datos_procesados/dataset_riesgo_despliegue_v1.csv`, `_v1_1.csv`, `_v2.csv` | Sí | Se clona |
| Figuras (`figuras/`, `informes/figuras/`), informes y diagramas (`docs/`) | Sí | Se clona |
| **Base de datos** (usuarios, repositorios, análisis, decisiones, informes) | **No** | Respaldo `.dump` que se pasa **por un medio privado** (§6) |
| **`backend/.env`** (claves y contraseñas) | **No** | Cada persona crea el suyo desde `backend/.env.example` con **sus propias** claves (§5) |
| `backend/venv/`, `frontend/node_modules/` | No | Se instalan (§4) |
| `informes/cache_filtrado/` (≈ 49 MB: caché de la API de GitHub y etiquetas de la regla 7) | No | **No hace falta para usar la plataforma.** Solo para volver a construir el dataset v2 (§10); si se necesita, se pasa comprimida por un medio privado |
| `Datos/runs.json.gz` (GHALogs, ≈ GB) | No | Solo para reproducir v1/v1.1; se descarga de Zenodo (registro 14796970) |
| `logs/` | No | Se crea sola con el análisis en lote |

> **El respaldo de la base se comparte solo por un medio privado** (unidad de
> red o carpeta en la nube con acceso restringido a esa persona, memoria USB).
> **Nunca por GitHub** ni por un enlace público: contiene las cuentas de
> usuario (con sus correos y contraseñas cifradas) y todo el historial de la
> plataforma. El repositorio es público.

## 2. Requisitos

- **Git**.
- **Python 3.12** (probado con 3.12.10).
- **Node.js 20 o superior** (probado con 24).
- **PostgreSQL 16** (instalador de EDB; anote la contraseña del usuario
  `postgres`). Sus programas (`pg_dump`, `pg_restore`, `psql`) deben estar en
  el PATH o en `C:\Program Files\PostgreSQL\16\bin` (los scripts los buscan ahí).
- **Token de GitHub** de solo lectura (para los análisis; §5).
- Opcional: **clave de Claude** (o de Gemini) para que la IA redacte el texto
  del análisis. Sin clave se usan las recomendaciones por reglas.
- Opcional: **cuenta de Gmail con contraseña de aplicación** para los correos
  de restablecimiento de contraseña. Sin correo, los mensajes salen en la
  consola del backend.

## 3. Clonar

```powershell
cd $HOME\Desktop
git clone https://github.com/ErickTerranova2004/Proyecto-de-titulaci-n-.git tesis
cd tesis
git checkout feature/100-repos-desplegados
```

Todos los comandos siguientes se ejecutan desde la carpeta `tesis`.

## 4. Instalar dependencias

```powershell
py -3.12 -m venv backend\venv
backend\venv\Scripts\python.exe -m pip install -r backend\requirements.txt
cd frontend; npm ci; cd ..
```

## 5. Crear `backend\.env` con sus propias claves

```powershell
Copy-Item backend\.env.example backend\.env
code backend\.env
```

Complete al menos:

| Variable | Valor |
|---|---|
| `DJANGO_SECRET_KEY` | Una clave **nueva**, no la de otra persona. Genérela con `backend\venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(50))"` y péguela |
| `POSTGRES_DB` | `riesgo_despliegue` |
| `POSTGRES_USER` / `POSTGRES_PASSWORD` | Los de **su** PostgreSQL (normalmente `postgres` y la contraseña que eligió al instalarlo) |
| `GITHUB_TOKEN` | Su token: GitHub → Settings → Developer settings → *Fine-grained tokens*, acceso a repositorios públicos, permisos de solo lectura `Actions`, `Contents` y `Metadata` |
| `CLAUDE_API_KEY` (opcional) | Su clave de https://platform.claude.com |
| `EMAIL_*` (opcional) | Ver los comentarios de `.env.example` (Gmail con contraseña de aplicación) |

Reglas:
- **`backend\.env` nunca se sube a GitHub** (está en `.gitignore`) ni se envía
  a otra persona. Cada quien usa sus propias claves; no se comparten tokens.
- Si alguna vez se publica por error, cambie de inmediato las claves que
  contenía (token de GitHub, claves de IA, contraseña de aplicación).

## 6. Restaurar la base de datos

Quien tiene los datos exporta un respaldo (en su equipo):

```powershell
powershell -ExecutionPolicy Bypass -File scripts\exportar_datos.ps1
```

Crea `..\tesis_respaldos\riesgo_despliegue_AAAAMMDD_HHMMSS_exportado.dump`
(fuera del repositorio; el script se niega a escribir dentro de él). No
incluye las sesiones abiertas. Ese archivo se entrega **por un medio privado**.

Quien lo recibe, con PostgreSQL encendido y `backend\.env` ya completado:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\importar_datos.ps1 -Respaldo C:\ruta\riesgo_despliegue_AAAAMMDD_HHMMSS_exportado.dump
```

El script crea la base si no existe, restaura el respaldo (a nombre de su
usuario de PostgreSQL) y aplica las migraciones. Si la base ya existe con
datos, se detiene; para sustituirla, añada `-Reemplazar` (antes guarda un
respaldo de la base actual en `..\tesis_respaldos\`).

Después de restaurar:
- Las cuentas son las del respaldo. Pida al administrador su usuario y
  contraseña, o cree una cuenta propia con
  `cd backend; venv\Scripts\python.exe manage.py createsuperuser`.
- Compruebe en **Modelos** que aparecen **Random Forest (Principal)** (`v2`) y
  **XGBoost (Alternativo)** (`v2-xgb`).

**Sin respaldo (base vacía, sin los datos de la tesis):**

```powershell
cd backend
venv\Scripts\python.exe manage.py migrate
venv\Scripts\python.exe manage.py registrar_modelo --modelo v2
venv\Scripts\python.exe manage.py registrar_modelo --modelo v2-xgb --sin-activar
venv\Scripts\python.exe manage.py createsuperuser
```

## 7. Arrancar la plataforma

```powershell
powershell -ExecutionPolicy Bypass -File scripts\iniciar_demo.ps1
```

Detiene lo que haya en los puertos 8000 y 5174, aplica las migraciones,
abre el backend y el frontend cada uno en su ventana y abre
http://localhost:5174. Para detener la plataforma, cierre las dos ventanas.
Con `-RedLocal` también se abre desde el celular en la misma Wi-Fi (ver la
cabecera del script).

## 8. Programar el análisis en lote (opcional)

El lote analiza cada 4 h las ejecuciones nuevas de los repositorios del
dataset v2 con el modelo activo y enlaza el resultado real de los análisis
(validación prospectiva). Usa la cuenta interna `analisis_lote` (viene en el
respaldo; no la elimine) y la cuota de **su** `GITHUB_TOKEN` (hasta 1.500
llamadas por pasada).

> A partir de la importación, la base de cada equipo evoluciona por separado:
> los resultados de su lote no se suman a los del otro equipo.

En PowerShell, desde la carpeta `tesis`:

```powershell
$raiz = (Get-Location).Path
$accion = New-ScheduledTaskAction -Execute "wscript.exe" -Argument "//B //Nologo `"$raiz\scripts\analizar_lote_oculto.vbs`""
$disparador = New-ScheduledTaskTrigger -Daily -At "00:00"
$disparador.Repetition = (New-ScheduledTaskTrigger -Once -At "00:00" -RepetitionInterval (New-TimeSpan -Hours 4) -RepetitionDuration (New-TimeSpan -Days 1)).Repetition
$ajustes = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 2) -MultipleInstances IgnoreNew
Register-ScheduledTask -TaskPath "\tesis\" -TaskName analizar_lote -Action $accion -Trigger $disparador -Settings $ajustes
```

- Probar una pasada a mano: `scripts\analizar_lote.cmd`. Cada pasada queda en
  `logs\lote_AAAAMMDD.log` y termina con `=== Codigo de salida 0 (…)`.
- Estado: `Get-ScheduledTaskInfo -TaskPath "\tesis\" -TaskName analizar_lote`.
- Pausar o reanudar (p. ej. antes de migrar la base):
  `Disable-ScheduledTask` / `Enable-ScheduledTask` con los mismos parámetros.
- El lote se niega a correr si el modelo activo no tiene fecha de corte
  (v1 y v1.1): el modelo activo debe ser v2.

## 9. Pruebas

```powershell
cd backend; venv\Scripts\python.exe manage.py test riesgo; cd ..
cd frontend; npm test; npx vite build; cd ..
```

Las pruebas del backend crean su propia base temporal y nunca llaman a una
API de pago.

## 10. Reproducir el dataset v2 y el modelo (opcional)

No hace falta para usar la plataforma: el dataset y los modelos ya están en
el repositorio.

- **Dataset v2**: `backend\venv\Scripts\python.exe -X utf8 scripts\construir_dataset_v2.py`.
  Parte de `informes\orden_repos_curva.csv` (en el repositorio) y de
  `informes\cache_filtrado\etiquetas.json` (no versionado: pídalo por un medio
  privado). Consulta la API de GitHub con su token.
- **Modelo v2**: `backend\venv\Scripts\python.exe -X utf8 entrenar_modelos_v2.py`
  (lee `datos_procesados\dataset_riesgo_despliegue_v2.csv`).
- **v1 y v1.1** (trazabilidad): requieren `Datos\runs.json.gz` (GHALogs
  v1.0.1, Zenodo 14796970; verifique el MD5 de `registro_datasets.csv`) y los
  scripts `find_deploy_runs.py`, `label_deploy_runs.py`, `build_dataset.py`,
  `build_dataset_v1_1.py`, `train_models.py` y `compare_versions.py` (ver la
  cabecera de cada uno).

Consulte la cabecera de cada script para los parámetros.
