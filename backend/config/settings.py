import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR.parent / ".env")

DEBUG = os.getenv("DEBUG", "False") == "True"

SECRET_KEY = os.getenv("SECRET_KEY", "")
if not SECRET_KEY:
    if not DEBUG:
        raise ImproperlyConfigured("SECRET_KEY must be set when DEBUG is off")
    SECRET_KEY = "dev-only-not-secret"

# Not required at startup so /api/health still answers before the key is added.
TOMTOM_API_KEY = os.getenv("TOMTOM_API_KEY", "")

ALLOWED_HOSTS = [".vercel.app", "localhost", "127.0.0.1"]

INSTALLED_APPS = ["rest_framework", "routing"]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

# Stateless API on serverless: no database, sessions or auth.
DATABASES = {}

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
    "UNAUTHENTICATED_USER": None,
    "EXCEPTION_HANDLER": "routing.api.errors.api_exception_handler",
}

APPEND_SLASH = False
USE_TZ = True
TIME_ZONE = "UTC"

# Timings of upstream calls show up in Vercel's runtime logs.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "loggers": {
        "routing": {"handlers": ["console"], "level": "INFO"},
        # httpx logs full request URLs at INFO, and the TomTom key is in the query string.
        "httpx": {"level": "WARNING"},
        "httpcore": {"level": "WARNING"},
    },
}
