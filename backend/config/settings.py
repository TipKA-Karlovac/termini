"""Postavke projekta. Sve što se razlikuje po okruženju dolazi iz varijabli okruženja."""

import os
from pathlib import Path
from urllib.parse import unquote, urlsplit

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent


def _flag(name: str, default: bool = False) -> bool:
    return os.environ.get(name, "1" if default else "0").lower() in {"1", "true", "yes"}


def _list(name: str, default: str = "") -> list[str]:
    return [item.strip() for item in os.environ.get(name, default).split(",") if item.strip()]


def _database(url: str) -> dict:
    """SQLite bez ``DATABASE_URL``; inače PostgreSQL iz ``postgres://korisnik:lozinka@host:port/baza``."""
    if not url:
        return {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
            # Upis odmah zaključava bazu, pa dvije istodobne rezervacije ne mogu
            # obje proći provjeru slobodnog termina.
            "OPTIONS": {"transaction_mode": "IMMEDIATE"},
        }
    parts = urlsplit(url)
    if parts.scheme not in {"postgres", "postgresql"}:
        raise ImproperlyConfigured("DATABASE_URL mora početi s postgres:// ili postgresql://")
    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": parts.path.lstrip("/"),
        "USER": unquote(parts.username or ""),
        "PASSWORD": unquote(parts.password or ""),
        "HOST": parts.hostname or "",
        "PORT": str(parts.port or ""),
    }


DEBUG = _flag("DJANGO_DEBUG")

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")
if not SECRET_KEY:
    if not DEBUG:
        raise ImproperlyConfigured("Postavite DJANGO_SECRET_KEY (ili DJANGO_DEBUG=1 za razvoj).")
    SECRET_KEY = "samo-za-razvoj-nije-tajna"

ALLOWED_HOSTS = _list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1" if DEBUG else "")

# Adresa web sučelja; koristi se za poveznice u e-pošti.
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5173").rstrip("/")

# Web sučelje je jedino mjesto s kojeg se vlasnik prijavljuje, pa mu Django
# mora vjerovati i kad je na drugoj adresi od API-ja (npr. Vite u razvoju).
CSRF_TRUSTED_ORIGINS = sorted({FRONTEND_URL, *_list("DJANGO_CSRF_TRUSTED_ORIGINS")})

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "booking",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

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

DATABASES = {"default": _database(os.environ.get("DATABASE_URL", ""))}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "hr"
TIME_ZONE = "Europe/Zagreb"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30
    SECURE_CONTENT_TYPE_NOSNIFF = True

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework.authentication.SessionAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAdminUser"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    "DEFAULT_THROTTLE_RATES": {
        # Javni obrazac nema prijavu, pa broj pokušaja ograničavamo po IP adresi.
        "booking": os.environ.get("BOOKING_THROTTLE", "20/hour"),
        "login": os.environ.get("LOGIN_THROTTLE", "10/hour"),
    },
}

# --- e-pošta -----------------------------------------------------------------

if os.environ.get("EMAIL_HOST"):
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_HOST = os.environ["EMAIL_HOST"]
    EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
    EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
    EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
    EMAIL_USE_TLS = _flag("EMAIL_USE_TLS", default=True)
else:
    # Bez poslužitelja e-pošte poruke se ispisuju u konzolu.
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "rezervacije@example.com")

# --- rezervacije -------------------------------------------------------------

BUSINESS_NAME = os.environ.get("BUSINESS_NAME", "Salon Primjer")

# Razmak između ponuđenih početaka termina.
BOOKING_SLOT_STEP_MINUTES = int(os.environ.get("BOOKING_SLOT_STEP_MINUTES", "15"))
# Najkraće vrijeme od sada do početka termina koji se još može rezervirati.
BOOKING_MIN_LEAD_MINUTES = int(os.environ.get("BOOKING_MIN_LEAD_MINUTES", "60"))
# Koliko dana unaprijed se može rezervirati.
BOOKING_MAX_DAYS_AHEAD = int(os.environ.get("BOOKING_MAX_DAYS_AHEAD", "30"))
# Do koliko sati prije početka klijent može sam otkazati.
BOOKING_CANCEL_UNTIL_HOURS = int(os.environ.get("BOOKING_CANCEL_UNTIL_HOURS", "2"))
