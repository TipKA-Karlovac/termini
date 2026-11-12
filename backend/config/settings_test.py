"""Postavke za testove: brže lozinke, e-pošta u memoriji, bez ograničenja pokušaja."""

import os

os.environ.setdefault("DJANGO_DEBUG", "1")

from .settings import *  # noqa: F403
from .settings import REST_FRAMEWORK

DEBUG = False
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
FRONTEND_URL = "https://termini.test"
CSRF_TRUSTED_ORIGINS = [FRONTEND_URL]
BUSINESS_NAME = "Salon Test"

BOOKING_SLOT_STEP_MINUTES = 15
BOOKING_MIN_LEAD_MINUTES = 60
BOOKING_MAX_DAYS_AHEAD = 30
BOOKING_CANCEL_UNTIL_HOURS = 2

REST_FRAMEWORK = {
    **REST_FRAMEWORK,
    "DEFAULT_THROTTLE_RATES": {"booking": "1000/hour", "login": "1000/hour"},
}
