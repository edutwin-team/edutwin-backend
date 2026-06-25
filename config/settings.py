"""
Django settings for config project.
"""

from pathlib import Path
import os
import dj_database_url
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# ---------------------------------------------------------
# 1. GESTION DE L'ENVIRONNEMENT (DEV vs PROD)
# ---------------------------------------------------------
# On définit une variable ENVIRONMENT (par défaut 'development')
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
IS_PRODUCTION = ENVIRONMENT == "production"
IN_GITHUB_ACTIONS = os.getenv("GITHUB_ACTIONS") == "true"

# SECURITY WARNING: keep the secret key used in production secret!
# En prod, on exige que la clé soit dans les variables d'env
if IS_PRODUCTION and not os.getenv("SECRET_KEY"):
    raise ValueError("La variable SECRET_KEY est obligatoire en production")

SECRET_KEY = os.getenv("SECRET_KEY", "django-insecure-dev-key-change-me")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = not IS_PRODUCTION

if IS_PRODUCTION:
    # En prod, on lit la variable. Par défaut, on autorise tous les sous-domaines Render
    allowed_hosts_env = os.getenv("ALLOWED_HOSTS", ".onrender.com")
    ALLOWED_HOSTS = [host.strip() for host in allowed_hosts_env.split(",")]
else:
    # En dev, on autorise juste le local
    ALLOWED_HOSTS = ["localhost", "127.0.0.1"]


# ---------------------------------------------------------
# 2. BASE DE DONNÉES (SQLite pour les tests CI, Supabase sinon)
# ---------------------------------------------------------
if IN_GITHUB_ACTIONS:
    # Pour le CI : on utilise SQLite en mémoire. C'est ultra rapide et ne nécessite aucun secret.
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
        }
    }
else:
    # Pour DEV et PROD : on utilise Supabase
    URL_DB = os.getenv("SUPABASE_DB_URL")
    if not URL_DB:
        raise ValueError("SUPABASE_DB_URL is not set")
    DATABASES = {"default": dj_database_url.parse(URL_DB)}


# ---------------------------------------------------------
# 3. APPLICATIONS & MIDDLEWARE
# ---------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Tes apps
    "rest_framework",
    "corsheaders",
    "django_filters",
    "django_celery_results",
    "django_celery_beat",
    "drf_spectacular",
    "user",
    "twins",
    "content",
    "simulation",
    "insights",
    "dashboard",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
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


# ---------------------------------------------------------
# 4. SÉCURITÉ, COOKIES & CORS
# ---------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.UserRateThrottle",
        "rest_framework.throttling.AnonRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "user": "5000/day",
        "anon": "100/hour",
    },
}

# CORS & CSRF : On les rend dynamiques pour la prod
if IS_PRODUCTION:
    # En prod, on lit depuis les variables d'environnement
    # .rstrip('/') supprime automatiquement le slash de fin s'il y en a un (pour éviter l'erreur CORS E014)
    cors_env = os.getenv("CORS_ALLOWED_ORIGINS", "")
    csrf_env = os.getenv("CSRF_TRUSTED_ORIGINS", "")

    CORS_ALLOWED_ORIGINS = [
        url.strip().rstrip("/") for url in cors_env.split(",") if url.strip()
    ]
    CSRF_TRUSTED_ORIGINS = [
        url.strip().rstrip("/") for url in csrf_env.split(",") if url.strip()
    ]
else:
    # En dev, valeurs par défaut
    CORS_ALLOWED_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]
    CSRF_TRUSTED_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]

CORS_ALLOW_CREDENTIALS = True

# Les cookies doivent être sécurisés (HTTPS) en production
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = IS_PRODUCTION  # True en prod, False en dev
CSRF_COOKIE_SECURE = IS_PRODUCTION  # True en prod, False en dev


# ---------------------------------------------------------
# 5. CELERY & INTERNATIONALIZATION
# ---------------------------------------------------------
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = "django-db"
CELERY_CACHE_BACKEND = "django-cache"

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Europe/Paris"
USE_I18N = True
USE_TZ = True


# ---------------------------------------------------------
# 6. FICHIERS STATIQUES (Requis pour Render)
# ---------------------------------------------------------
STATIC_URL = "static/"
# Render a besoin de STATIC_ROOT pour la commande `collectstatic` pendant le build
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "user.User"
