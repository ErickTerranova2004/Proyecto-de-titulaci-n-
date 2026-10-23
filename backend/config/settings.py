"""Configuración de la plataforma de riesgo de despliegue.

Los secretos (SECRET_KEY, GITHUB_TOKEN, credenciales de PostgreSQL) se leen
de variables de entorno o de backend/.env, nunca del código fuente.
"""

import os
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
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
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
    "DEFAULT_THROTTLE_RATES": {"user": "120/hour"},
}

CORS_ALLOWED_ORIGINS = [o for o in os.environ.get(
    "CORS_ALLOWED_ORIGINS", "http://localhost:5173").split(",") if o]

CACHES = {
    "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}
}

# Integración con GitHub y modelo.
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_API_URL = "https://api.github.com"
MODELOS_DIR = Path(os.environ.get("MODELOS_DIR", PROJECT_DIR / "modelos"))

# Correo de asignaciones al desarrollador: desactivado por defecto. Se envía
# solo con CORREO_ASIGNACIONES=1; sin EMAIL_HOST se usa el backend de consola
# (el mensaje se escribe en la terminal del servidor, útil en desarrollo).
CORREO_ASIGNACIONES = os.environ.get("CORREO_ASIGNACIONES", "") == "1"
EMAIL_HOST = os.environ.get("EMAIL_HOST", "")
if EMAIL_HOST:
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
    EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
    EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
    EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "1") == "1"
else:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL",
                                    "riesgo-despliegue@localhost")

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
