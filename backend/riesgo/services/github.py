"""Cliente mínimo de la API REST de GitHub.

- Autenticación con GITHUB_TOKEN (variable de entorno); sin token el límite
  es de 60 solicitudes por hora.
- Respuestas en caché: los commits son inmutables (24 h); el historial de
  ejecuciones cambia (5 min).
- Errores tipificados para responder al usuario sin exponer detalles.
"""

import logging
import re

import requests
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

REPO = re.compile(r"^[A-Za-z0-9_.-]{1,100}/[A-Za-z0-9_.-]{1,100}$")
WORKFLOW = re.compile(r"^\.github/workflows/[A-Za-z0-9_./-]{1,200}\.ya?ml$")
SHA = re.compile(r"^[0-9a-fA-F]{7,40}$")


class GitHubError(Exception):
    """Error genérico de GitHub."""

    def __init__(self, mensaje="", estado=None):
        super().__init__(mensaje)
        self.estado = estado


class NoEncontrado(GitHubError):
    """Recurso inexistente o sin permisos de lectura."""


class RamaNoEncontrada(GitHubError):
    """La rama indicada no existe en el repositorio."""

    def __init__(self, rama, principal):
        super().__init__(f"La rama {rama} no existe")
        self.rama = rama
        self.principal = principal


class LimiteExcedido(GitHubError):
    """Límite de solicitudes agotado."""

    def __init__(self, reinicio):
        super().__init__("Límite de la API de GitHub agotado")
        self.reinicio = reinicio


class GitHubClient:
    def __init__(self, token=None, base_url=None, sesion=None):
        self.token = settings.GITHUB_TOKEN if token is None else token
        self.base_url = base_url or settings.GITHUB_API_URL
        self.sesion = sesion or requests.Session()

    def _cabeceras(self):
        cabeceras = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "plataforma-riesgo-despliegue",
        }
        if self.token:
            cabeceras["Authorization"] = f"Bearer {self.token}"
        return cabeceras

    def get(self, ruta, params=None, ttl=300):
        clave = f"gh:{ruta}:{sorted((params or {}).items())}"
        guardado = cache.get(clave)
        if guardado is not None:
            return guardado
        try:
            respuesta = self.sesion.get(f"{self.base_url}{ruta}",
                                        headers=self._cabeceras(),
                                        params=params, timeout=20)
        except requests.RequestException as exc:
            logger.warning("Error de red con GitHub en %s: %s", ruta,
                           type(exc).__name__)
            raise GitHubError("No se pudo conectar con GitHub") from exc

        restantes = respuesta.headers.get("X-RateLimit-Remaining")
        if respuesta.status_code in (403, 429) and restantes == "0":
            raise LimiteExcedido(respuesta.headers.get("X-RateLimit-Reset"))
        if respuesta.status_code in (401, 403, 404):
            # Un repositorio privado sin permisos también responde 404.
            raise NoEncontrado(ruta)
        if respuesta.status_code >= 400:
            logger.warning("GitHub respondió %s en %s",
                           respuesta.status_code, ruta)
            raise GitHubError(f"GitHub respondió {respuesta.status_code}",
                              respuesta.status_code)
        datos = respuesta.json()
        cache.set(clave, datos, ttl)
        return datos

    def repositorio(self, repo):
        # Un repositorio renombrado redirige (301) al nombre actual.
        return self.get(f"/repos/{repo}", ttl=3600)

    def commit(self, repo, sha):
        return self.get(f"/repos/{repo}/commits/{sha}", ttl=86400)

    def ultimo_commit(self, repo, rama):
        try:
            return self.get(f"/repos/{repo}/commits/{rama}", ttl=60)
        except GitHubError as exc:
            # GitHub responde 422 si la rama no existe en el repositorio.
            if exc.estado != 422:
                raise
            principal = self.repositorio(repo).get("default_branch")
            if not principal or principal == rama:
                raise
            raise RamaNoEncontrada(rama, principal) from exc

    def workflow(self, repo, workflow_path):
        archivo = workflow_path.rsplit("/", 1)[-1]
        return self.get(f"/repos/{repo}/actions/workflows/{archivo}")

    def ejecuciones_workflow(self, repo, workflow_path, n=20, head_sha=None):
        archivo = workflow_path.rsplit("/", 1)[-1]
        params = {"per_page": n}
        if head_sha:
            params["head_sha"] = head_sha
        datos = self.get(f"/repos/{repo}/actions/workflows/{archivo}/runs",
                         params=params, ttl=60 if head_sha else 300)
        return datos.get("workflow_runs", [])

    def limite(self):
        """Estado del límite de la API (esta consulta no consume cuota)."""
        respuesta = self.sesion.get(f"{self.base_url}/rate_limit",
                                    headers=self._cabeceras(), timeout=20)
        if respuesta.status_code >= 400:
            raise GitHubError(f"GitHub respondió {respuesta.status_code}")
        return respuesta.json().get("rate", {})

    def jobs_intento(self, repo, run_id, intento):
        datos = self.get(
            f"/repos/{repo}/actions/runs/{run_id}/attempts/{intento}/jobs",
            params={"per_page": 100}, ttl=3600)
        return datos.get("jobs", [])

    def ejecuciones_repositorio(self, repo, n=100):
        datos = self.get(f"/repos/{repo}/actions/runs",
                         params={"per_page": n})
        return datos.get("workflow_runs", [])
