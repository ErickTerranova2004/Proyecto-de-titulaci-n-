# Usuarios de prueba para revisar la interfaz

Solo para el entorno local de desarrollo. Las contraseñas son **de prueba**
(no se usan en ningún otro sitio); cámbielas o borre los usuarios antes de
cualquier despliegue real.

| Usuario | Rol | Contraseña de prueba | Repositorios |
|---|---|---|---|
| `revision_admin` | Administrador | `Revision-Admin-2026` | Ve todos (además tiene asignados los 198 del dataset v2) |
| `revision_lider` | Líder técnico | `Revision-Lider-2026` | Los 198 del dataset v2 |
| `revision_dev` | Desarrollador | `Revision-Dev-2026` | Los 198 del dataset v2 |
| `analisis_lote` | Sin rol | Sin contraseña (no puede iniciar sesión) | Autor de las predicciones del análisis en lote |

Los tres primeros forman el grupo que revisa la validación prospectiva de v2.
El desarrollador solo ve sus propios análisis; las predicciones del lote
(usuario `analisis_lote`) las ven el líder técnico y el administrador.

## Cómo se crearon

```powershell
cd backend
venv\Scripts\python.exe manage.py crear_usuario revision_admin --rol administrador --password Revision-Admin-2026
venv\Scripts\python.exe manage.py crear_usuario revision_lider --rol lider_tecnico --password Revision-Lider-2026
venv\Scripts\python.exe manage.py crear_usuario revision_dev --rol desarrollador --password Revision-Dev-2026
venv\Scripts\python.exe manage.py registrar_repos_v2 --validado-por revision_admin `
    --asignar revision_dev revision_lider revision_admin --aplicar
venv\Scripts\python.exe manage.py analizar_lote --usuario analisis_lote
```

`registrar_repos_v2` no carga ejecuciones históricas. `analizar_lote` se puede
repetir: solo analiza las ejecuciones posteriores a la fecha de corte que
hayan terminado desde la vez anterior (`--contar` solo las cuenta).

## Levantar la plataforma

Requisitos: PostgreSQL encendido, `backend\.env` configurado, `backend\venv`
con las dependencias y `npm ci` ejecutado en `frontend`.

Todo en uno (abre dos ventanas y el navegador):

```powershell
powershell -ExecutionPolicy Bypass -File scripts\iniciar_demo.ps1
```

O por separado, cada uno en su terminal:

```powershell
# Backend (http://127.0.0.1:8000)
cd backend
venv\Scripts\python.exe manage.py migrate
venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000

# Frontend (http://localhost:5174)
cd frontend
npx vite --port 5174
```

Para ver dos perfiles a la vez, use ventanas distintas (normal, incógnito u
otro navegador): la sesión se guarda en el navegador.
