# Manual de instalación y ejecución (Windows + VS Code)

## 1. Requisitos

- Python 3.12 o superior (probado con 3.14) y Node.js 20 o superior (probado con 24).
- PostgreSQL 16 o superior para el uso real. Sin PostgreSQL, el backend usa SQLite, pero solo para desarrollo.
- Un token de GitHub de solo lectura (recomendado). Sin token, la API permite 60 solicitudes por hora y cada análisis consume unas 3.

## 2. Entorno de Python

Abra una terminal de VS Code (Ctrl+ñ) en `Fase2_Tesis`:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
```

## 3. Configuración del backend

1. Copie `backend\.env.example` como `backend\.env`.
2. En `DJANGO_SECRET_KEY` ponga una clave aleatoria. Puede generarla con:
   `.\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(50))"`
3. **Token de GitHub:** en GitHub → Settings → Developer settings → *Fine-grained tokens*, cree un token con permisos de solo lectura `Actions`, `Contents` y `Metadata`. Péguelo en `GITHUB_TOKEN`. **Nunca suba `backend\.env` a un repositorio**; ya está en `.gitignore`.
4. **PostgreSQL:** instale PostgreSQL y cree la base de datos con `createdb -U postgres riesgo_despliegue`. Después complete `POSTGRES_DB=riesgo_despliegue` y `POSTGRES_PASSWORD` en `backend\.env`.

## 4. Preparar la base de datos y el modelo

```powershell
cd backend
..\.venv\Scripts\python.exe manage.py migrate
..\.venv\Scripts\python.exe manage.py registrar_modelo --modelo v1
..\.venv\Scripts\python.exe manage.py registrar_modelo --modelo v1.1
..\.venv\Scripts\python.exe manage.py validar_workflows_dataset
..\.venv\Scripts\python.exe manage.py createsuperuser
```

- `registrar_modelo` crea los roles `desarrollador`, `lider_tecnico` y `administrador`, y registra y activa el modelo indicado. El último registrado queda activo (v1.1); v1 queda inactivo para trazabilidad.
- `validar_workflows_dataset` registra y valida los 639 workflows del dataset v1.1 (ver `informes\workflows_validados.md`).
- En el admin (http://127.0.0.1:8000/admin/):
  - **Users → Groups:** asigne el rol a cada usuario.
  - **Accesos a repositorios:** asigne a cada desarrollador o líder los repositorios que puede consultar. Sin acceso no verá ningún repositorio.
  - **Workflows:** para usar un repositorio propio, cree el repositorio y su workflow, márquelo como validado y escriba la evidencia (por ejemplo, el paso del YAML que despliega y el entorno). Ajuste `patron_paso_despliegue` si los nombres de sus pasos de despliegue no contienen palabras como "deploy".

## 5. Ejecutar

Use dos terminales:

```powershell
# Terminal 1 (backend)
cd backend
..\.venv\Scripts\python.exe manage.py runserver

# Terminal 2 (frontend)
cd frontend
npm install
npm run dev
```

Abra http://localhost:5173 e inicie sesión con un usuario que tenga un rol asignado.

## 6. Pruebas

```powershell
cd backend
..\.venv\Scripts\python.exe manage.py test riesgo
```

Resultado esperado: `Ran 37 tests ... OK`.

## 7. Reproducir el pipeline de datos y el modelo

Requiere `Datos\runs.json.gz` (GHALogs v1.0.1, Zenodo 14796970; verifique el MD5 de `registro_datasets.csv`). Cada lectura completa del archivo tarda varios minutos.

```powershell
py .\find_deploy_runs.py --runs .\Datos\runs.json.gz --out .\informes\informe_deploy_runs.md --csv .\informes\deploy_runs.csv
py .\label_deploy_runs.py --runs .\Datos\runs.json.gz --deploy-csv .\informes\deploy_runs.csv --out .\informes\informe_niveles_despliegue.md --csv .\informes\deploy_runs_niveles.csv
# v1 (se conserva para trazabilidad; build_dataset.py escribe dataset_riesgo_despliegue.csv,
# que se renombró a dataset_riesgo_despliegue_v1.csv)
.\.venv\Scripts\python.exe .\build_dataset.py --runs .\Datos\runs.json.gz --labels .\informes\deploy_runs_niveles.csv --out-dir .\datos_procesados --report .\informes\informe_calidad_dataset_v1.md
.\.venv\Scripts\python.exe .\train_models.py --data .\datos_procesados\dataset_riesgo_despliegue_v1.csv --model-dir .\modelos --fig-dir .\informes\figuras --report .\informes\fase5_modelos_v1.md --version v1

# v1.1 (vigente): corrige las reglas que dependían del resultado
.\.venv\Scripts\python.exe .\build_dataset_v1_1.py --runs .\Datos\runs.json.gz --deploy-csv .\informes\deploy_runs.csv --v1-dataset .\datos_procesados\dataset_riesgo_despliegue_v1.csv --v1-niveles .\informes\deploy_runs_niveles.csv --historial .\datos_procesados\historial_runs.pkl --out .\datos_procesados\dataset_riesgo_despliegue_v1_1.csv --runs-out .\informes\deploy_runs_v1_1.csv --report .\informes\informe_calidad_dataset_v1_1.md
.\.venv\Scripts\python.exe .\train_models.py --data .\datos_procesados\dataset_riesgo_despliegue_v1_1.csv --model-dir .\modelos --fig-dir .\informes\figuras --report .\informes\fase5_modelos_v1_1.md --version v1.1
.\.venv\Scripts\python.exe .\compare_versions.py --a v1 .\datos_procesados\dataset_riesgo_despliegue_v1.csv --b v1.1 .\datos_procesados\dataset_riesgo_despliegue_v1_1.csv --model-dir .\modelos --report .\informes\fase5_modelos_v1_1.md
```

Las semillas aleatorias están fijadas (42). `build_dataset.py` guarda una caché en `datos_procesados\historial_runs.pkl`; bórrela para releer `runs.json.gz`.
