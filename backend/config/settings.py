"""Configuración de la plataforma de riesgo de despliegue.

Los secretos (SECRET_KEY, GITHUB_TOKEN, credenciales de PostgreSQL) se leen
de variables de entorno o de backend/.env, nunca del código fuente.
"""

import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_DIR = BASE_DIR.parent


def cargar_env(ruta):
    """Carga un archivo .env sencillo (CLAVE=valor) sin sobrescribir."""
    if not ruta.exists():
        return
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        clave, valor = linea.split("=", 1)
        os.environ.setdefault(clave.strip(), valor.strip())


cargar_env(BASE_DIR / ".env")

DEBUG = os.environ.get("DJANGO_DEBUG", "0") == "1"
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")
if not SECRET_KEY:
    if not DEBUG:
        raise RuntimeError("Defina DJANGO_SECRET_KEY en backend/.env")
    SECRET_KEY = "solo-desarrollo-no-usar-en-produccion"

ALLOWED_HOSTS = [h for h in os.environ.get(
    "DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if h]

# Modo red local (p. ej. abrir la plataforma o el enlace de restablecimiento
# desde un celular en la misma Wi-Fi): IP_RED_LOCAL=192.168.x.y añade esa IP a
# ALLOWED_HOSTS, CORS y CSRF, y FRONTEND_URL apunta a http://IP:PUERTO_FRONTEND
# salvo que FRONTEND_URL se fije aparte. scripts/iniciar_demo.ps1 -RedLocal
# la define al arrancar (sin tocar este archivo ni el .env).
IP_RED_LOCAL = os.environ.get("IP_RED_LOCAL", "").strip()
PUERTO_FRONTEND = os.environ.get("PUERTO_FRONTEND", "5174").strip() or "5174"
ORIGENES_RED_LOCAL = ([f"http://{IP_RED_LOCAL}:{PUERTO_FRONTEND}",
                       f"http://{IP_RED_LOCAL}:8000"] if IP_RED_LOCAL else [])
if IP_RED_LOCAL and IP_RED_LOCAL not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(IP_RED_LOCAL)

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework.authtoken",
    "corsheaders",
    "riesgo",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    # usu_creacion/usu_modificacion: el usuario de la petición (auditoria.py).
    "riesgo.auditoria.MiddlewareAuditoria",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# PostgreSQL si POSTGRES_DB está definido; SQLite solo para desarrollo.
if os.environ.get("POSTGRES_DB"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ["POSTGRES_DB"],
            "USER": os.environ.get("POSTGRES_USER", "postgres"),
            "PASSWORD": os.environ.get("POSTGRES_PASSWORD", ""),
            "HOST": os.environ.get("POSTGRES_HOST", "localhost"),
            "PORT": os.environ.get("POSTGRES_PORT", "5432"),
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation."
             "UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation."
             "CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation."
             "NumericPasswordValidator"},
]

LANGUAGE_CODE = "es"
TIME_ZONE = "America/Guayaquil"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.TokenAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.UserRateThrottle",
    ],
    # La interfaz consulta sola (asignaciones, seguimiento de la ejecución
    # real cada 30 s), por eso el límite deja margen al uso normal.
    # «restablecer»: peticiones públicas de restablecimiento de contraseña
    # (por IP), para que no se usen para enviar correos en masa.
    "DEFAULT_THROTTLE_RATES": {"user": "1000/hour", "restablecer": "20/hour"},
}

CORS_ALLOWED_ORIGINS = [o for o in os.environ.get(
    "CORS_ALLOWED_ORIGINS", "http://localhost:5173").split(",") if o]
CORS_ALLOWED_ORIGINS += [o for o in ORIGENES_RED_LOCAL
                         if o not in CORS_ALLOWED_ORIGINS]
# El administrador de Django (/admin, vía el proxy de Vite) desde otra IP.
CSRF_TRUSTED_ORIGINS = list(ORIGENES_RED_LOCAL)

CACHES = {
    "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}
}

# Integración con GitHub y modelo.
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_API_URL = "https://api.github.com"
MODELOS_DIR = Path(os.environ.get("MODELOS_DIR", PROJECT_DIR / "modelos"))

# Análisis explicado con IA (riesgo/services/analisis_ia.py): la IA solo
# redacta el texto; probabilidad, nivel, SHAP y recomendación son del
# modelo. IA_PROVEEDOR = claude | gemini | reglas. Sin la clave del
# proveedor, o si falla o tarda más de IA_TIMEOUT segundos, se usan las
# recomendaciones por reglas.
IA_PROVEEDOR = os.environ.get("IA_PROVEEDOR", "claude").strip().lower()
CLAUDE_API_KEY = os.environ.get("CLAUDE_API_KEY", "")
CLAUDE_MODELO = os.environ.get("CLAUDE_MODELO", "claude-haiku-5-5")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODELO = os.environ.get("GEMINI_MODELO", "gemini-3.5-flash")
IA_TIMEOUT = int(os.environ.get("IA_TIMEOUT", "90"))
# Las pruebas nunca llaman a una API de IA de pago (cada prueba que la
# simula fija su proveedor con override_settings).
if sys.argv[1:2] == ["test"]:
    IA_PROVEEDOR = "reglas"

# Correo (restablecimiento de contraseña y, con CORREO_ASIGNACIONES=1,
# asignaciones al desarrollador). Sin EMAIL_HOST se usa el backend de consola:
# el mensaje se escribe en la terminal del servidor y la interfaz lo avisa.
CORREO_ASIGNACIONES = os.environ.get("CORREO_ASIGNACIONES", "") == "1"
EMAIL_HOST = os.environ.get("EMAIL_HOST", "")
if EMAIL_HOST:
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_PORT = int(os.environ.get("EMAIL_PORT") or "587")
    EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
    # Gmail muestra la contraseña de aplicación en grupos («abcd efgh …»):
    # se admite pegada con o sin espacios.
    EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "").replace(
        " ", "")
    EMAIL_USE_TLS = (os.environ.get("EMAIL_USE_TLS") or "1").strip().lower() \
        in ("1", "true", "si", "sí", "yes")
    EMAIL_TIMEOUT = 20
else:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
# `or`: una clave presente pero vacía en .env también toma el valor por defecto.
DEFAULT_FROM_EMAIL = (os.environ.get("DEFAULT_FROM_EMAIL")
                      or "riesgo-despliegue@localhost")
CORREO_CONFIGURADO = bool(EMAIL_HOST)

# Dirección del frontend: el enlace del correo de restablecimiento apunta a
# FRONTEND_URL/restablecer/<uid>/<token>.
FRONTEND_URL = (os.environ.get("FRONTEND_URL")
                or (f"http://{IP_RED_LOCAL}:{PUERTO_FRONTEND}" if IP_RED_LOCAL
                    else "http://localhost:5174")).rstrip("/")
# Validez del enlace de restablecimiento (PasswordResetTokenGenerator): 1 hora.
# Es de un solo uso: el token depende del hash de la contraseña, que cambia.
PASSWORD_RESET_TIMEOUT = 3600

# Planificador: días (a partir de mañana) de las «Mejores ventanas».
PLANIFICADOR_DIAS_VENTANAS = int(
    os.environ.get("PLANIFICADOR_DIAS_VENTANAS") or "3")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "ocultar_secretos": {"()": "riesgo.logging_filters.OcultarSecretos"},
    },
    "handlers": {
        "consola": {
            "class": "logging.StreamHandler",
            "filters": ["ocultar_secretos"],
        },
    },
    "root": {"handlers": ["consola"], "level": "INFO"},
}
