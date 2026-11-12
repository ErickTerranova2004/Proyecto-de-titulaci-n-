# Estado del proyecto (para continuar en una sesión nueva)

Tesis: «Plataforma predictiva basada en IA para el riesgo de despliegue de
aplicaciones empresariales». Django/DRF + React/Vite, PostgreSQL, Random
Forest/XGBoost + SHAP, análisis de texto con Gemini.

Actualizado: 2026-11-12 · rama `feature/100-repos-desplegados` (publicada en
`origin`, **sin merge a `main`**).

## 1. Reglas acordadas (obligatorias)

1. **Responder siempre en español.**
2. **Nunca imprimir el `.env`** (`backend/.env`). Los valores se leen solo
   dentro del comando, sin mostrarlos:
   `v(){ grep "^$1=" backend/.env | cut -d= -f2- | tr -d '\r'; }`.
3. **Commit sí; push y merge solo cuando se pidan.** Nunca merge a `main`
   sin orden expresa. Antes de cada push: comprobar que no se suben `.env`,
   `logs/`, respaldos (`*.dump`) ni secretos (tokens, claves, contraseñas).
4. **Respaldo antes de tocar la base de datos**: `pg_dump -Fc` en
   `C:\Users\Administrator\Desktop\tesis_respaldos\` (fuera del repositorio)
   antes de cualquier migración o cambio de datos.
5. **Migraciones**: ensayarlas primero en una copia restaurada del respaldo
   (aplicar, revertir, volver a aplicar), luego en la base real.
6. **Tarea programada**: desactivarla antes de migrar y reactivarla al
   terminar (ver §5).
7. **Dataset congelado**: no reabrir la búsqueda de repositorios ni cambiar
   las reglas de etiquetado sin aprobación.
8. **Cambios grandes por etapas** y esperar aprobación entre etapas cuando
   así se pida.
9. Pruebas antes de cada commit: `venv\Scripts\python.exe manage.py test
   riesgo` (backend) y `npm test` + `npx vite build` (frontend).

## 2. Estado actual

### Dataset v2.0
- `datos_procesados/dataset_riesgo_despliegue_v2.csv`: 4.117 ejecuciones de
  198 repositorios reales (401 con y = 1, despliegue no completado).
- Etiquetas: y = 0 `despliegue_completado`, y = 1 `despliegue_no_completado`;
  el resto (`excluida_*`) no se evalúa. Etiquetado con los jobs de la API y
  el YAML del workflow en el commit de cada ejecución
  (`riesgo/services/etiquetado.py`, `verificacion.py`).
- Fecha de corte (última ejecución del entrenamiento):
  **2026-11-09T16:09:30Z** (`modelos/modelo_riesgo_v2.json`).

### Modelo v2 (activo)
- Random Forest, validación GroupKFold por repositorio: PR-AUC 0,415,
  ROC-AUC 0,803, recall y=1 0,536, precisión 0,517, F1 0,526, Brier 0,067.
  v1 y v1.1 están registrados e inactivos.
- Recomendación automática: nivel alto → «Solicitar revisión previa»;
  bajo/medio → «Permitir el despliegue». El líder técnico la acepta o la
  cambia (se guarda `acepta_recomendacion`).
- Gemini solo redacta el texto del análisis; si falla o tarda (`IA_TIMEOUT`),
  se usa el análisis por reglas (nunca Error 500).
- Supervisión prospectiva: cuenta solo ejecuciones posteriores al corte;
  excluye repos de demostración y de prueba. 542 predicciones de lote y 225
  interactivas en la base (12-nov).

### Plataforma
- 229 repositorios activos (198 del dataset v2 + 1 de demostración
  `ErickTerranova2004/demo-despliegue-riesgo` + 30 de casos de prueba);
  406 inactivos (históricos de GHALogs y otros), se conservan con su historial.
- «Nuevo análisis»: los repos con commits pendientes de desplegar salen
  primero («N commits pendientes») y rellenan SHA, rama y evento; aviso 409
  si el commit ya se desplegó o se está desplegando (se puede continuar).
- «Verificar resultado real»: enlaza la primera ejecución terminada del
  mismo workflow y commit que empiece después del análisis (ignora las
  `skipped`); seguimiento automático 30 s en el navegador y, además, cada
  pasada del lote.
- Usuarios activos: `admin` (superusuario), `revision_admin`,
  `revision_dev`, `revision_lider` (contraseñas de prueba en
  `datos_prueba/usuarios_prueba.md`) y `analisis_lote` (cuenta interna del
  lote: sin rol ni contraseña utilizable; **no eliminarla**). Las cuentas
  `prueba_*` se eliminaron y su historial pasó a las `revision_*` del mismo
  rol.
- «Último acceso» se registra al iniciar sesión (`riesgo/sesion.py`).
- El administrador puede eliminar cuentas con historial traspasándolo a otra
  cuenta activa del mismo rol o administradora.

### Base de datos y diagrama ER
- Nombres del ER (`docs/modelo_er.png`): tablas `mae_`, `trx_`, `int_`
  (migraciones 0016–0018); índices y restricciones `pk_/fk_/uk_/ck_/ix_/sq_`;
  vistas de solo lectura `seg_usuario`, `seg_grupo`, `int_usuario_grupo`,
  `seg_token` sobre las tablas de Django (`auth_*`, que se mantienen).
- Auditoría (migración 0019, `riesgo/auditoria.py`): `est_registro`
  (char(1), A/I, sin borrado lógico), `usu_creacion`, `fec_creacion`,
  `usu_modificacion`, `fec_modificacion` en las 11 tablas propias; se llenan
  en todas las vías de escritura (middleware para la API, `ComandoAuditado`
  para los comandos, `sistema` fuera de ambos).
- `backend/riesgo/tests/test_esquema_er.py` compara la base con el ER
  columna por columna.
- Diagrama actualizado: `docs/modelo_er_actualizado.drawio` y `.png`,
  generados con `backend\venv\Scripts\python.exe scripts\generar_diagrama_er.py --png`.
- Equivalencias y diferencias documentadas en `docs/arquitectura.md`.

### Tarea programada (análisis en lote)
- Tarea `tesis\analizar_lote` del Programador de tareas, cada 4 h desde las
  00:00, también con batería; la lanza oculta
  `scripts\analizar_lote_oculto.vbs` → `scripts\analizar_lote.cmd`.
  Log diario en `logs\lote_AAAAMMDD.log` (cada pasada termina con
  `=== Codigo de salida 0 (…)`).
- Cada pasada: (1) enlaza análisis interactivos pendientes (30 días),
  (2) analiza ejecuciones nuevas posteriores al corte (listado incremental,
  ETag; se salta las ya enlazadas a un análisis interactivo), (3) actualiza
  los commits pendientes por workflow. Gasto típico: 10–40 llamadas a la API
  (+ cientos de 304 sin coste).
- Comprobar: `Get-ScheduledTaskInfo -TaskPath "\tesis\" -TaskName analizar_lote`.
  Desactivar/activar: `Disable-ScheduledTask` / `Enable-ScheduledTask`
  (mismos parámetros).

### Levantar la plataforma
```powershell
cd backend; venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000 --noreload
cd frontend; npx vite --port 5174
```
(o `scripts\iniciar_demo.ps1`). Requiere PostgreSQL encendido.

### Respaldos recientes (`tesis_respaldos\`)
- `riesgo_despliegue_20261112_002918_antes_nombres_er.dump`
- `riesgo_despliegue_20261112_005202_antes_auditoria.dump`
- `riesgo_despliegue_20261112_033644_antes_quitar_prueba.dump`

## 3. Decisiones tomadas

| Decisión | Motivo |
|---|---|
| Mantener las tablas de usuarios de Django y exponer `seg_*` como vistas | Cambiar el modelo de usuario a mitad del proyecto obliga a rehacer migraciones, usuarios y tokens |
| `est_registro` sin borrado lógico ('E') | Cambiaría el comportamiento de todas las consultas y de las restricciones únicas |
| La IA (Gemini) solo redacta el análisis | La probabilidad, el nivel, los factores SHAP y la recomendación son del modelo |
| Lote: no analizar ejecuciones ya enlazadas a un análisis interactivo | Un despliegue no debe contar dos veces en la supervisión |
| Lote cada 4 h (no cada hora) | Las variables se reconstruyen al inicio de cada ejecución: la frecuencia no cambia el resultado y ahorra cuota |
| No filtrar repositorios en «Nuevo análisis»; avisar del commit ya desplegado | «Desplegado» depende del commit; la mayoría despliega con cada push |
| Cuentas con historial: eliminar solo traspasándolo | Conservar trazabilidad y métricas |
| Análisis de demostración y de prueba fuera de las métricas | No son validación del modelo |

## 4. Pendientes (por prioridad)

**Alta**
1. **Merge de `feature/100-repos-desplegados` a `main`**: todo está
   publicado en la rama; esperar orden expresa.
2. **Demostración con despliegues reales**: analizar EfileProxyServer
   (`fly-prod-release.yml`, evento `release`, rama `v1.5.4`) y lumos-web
   (`deploy-cloudrun-release.yaml`, rama `v2.0.25`) con el SHA de la cabeza
   de `main` justo antes de su próxima release; el lote enlaza el resultado.

**Media**
3. **Error del etiquetado con `\bplan\b`**: `PATRON_NO_DESPLIEGA` marca
   «no despliega» una variable `plan.txt` dentro de un script de despliegue
   (caso built-in-saudi). Corregirlo afecta al dataset congelado: requiere
   aprobación.
4. **Error boundary en React**: un error en un componente deja hoy toda la
   interfaz en blanco (pasó en el panel de administración con v2).
5. Actualizar el informe de supervisión de v2 en la tesis con los datos que
   sigue sumando el lote.

**Baja**
6. Análisis 683 y 686 del repo de demostración: siguen pendientes de su
   resultado real (fuera de métricas); se enlazan solos si se despliega la
   demo.
7. Etiquetas `sin_intento` restantes del lote (128 tras el re-etiquetado):
   revisar si alguna es sospechosa.
8. `datos_prueba/casos_prueba_30.md` nombra a las cuentas `prueba_*`
   eliminadas (registro histórico; se dejó tal cual).
