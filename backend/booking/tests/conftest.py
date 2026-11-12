from datetime import UTC, datetime, time
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

from booking.models import Service, WorkingHours

ZAGREB = ZoneInfo("Europe/Zagreb")

# Ponedjeljak. Svi testovi koriste ovaj dan kao „sada”, pa ne ovise o datumu pokretanja.
MONDAY = datetime(2026, 3, 2, 7, 0, tzinfo=ZAGREB)


def local(day: int, hour: int, minute: int = 0, month: int = 3) -> datetime:
    """Lokalno vrijeme u ožujku 2026. kao UTC, onako kako ga vraća API."""
    return datetime(2026, month, day, hour, minute, tzinfo=ZAGREB).astimezone(UTC)


@pytest.fixture(autouse=True)
def _clear_throttle_cache():
    cache.clear()


@pytest.fixture
def now(monkeypatch):
    """Zamrzava „sada” na ponedjeljak 2. 3. 2026. u 7:00."""
    monkeypatch.setattr("django.utils.timezone.now", lambda: MONDAY)
    return MONDAY


@pytest.fixture
def haircut(db):
    return Service.objects.create(name="Šišanje", duration_minutes=30, price=Decimal("15.00"))


@pytest.fixture
def colouring(db):
    return Service.objects.create(name="Bojanje", duration_minutes=90, price=Decimal("45.00"))


@pytest.fixture
def working_week(db):
    """Ponedjeljak–petak 8–12 i 14–18."""
    for weekday in range(5):
        WorkingHours.objects.create(weekday=weekday, opens=time(8), closes=time(12))
        WorkingHours.objects.create(weekday=weekday, opens=time(14), closes=time(18))


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def owner(django_user_model):
    return django_user_model.objects.create_user("vlasnik", password="tajna-lozinka", is_staff=True)


@pytest.fixture
def customer_data(haircut):
    return {
        "service": haircut.pk,
        "starts_at": local(2, 9).isoformat(),
        "customer_name": "Ana Anić",
        "customer_phone": "091 234 5678",
        "customer_email": "ana@example.com",
        "note": "",
    }
