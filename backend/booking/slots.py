"""Izračun slobodnih termina.

Sve se računa u UTC-u, a radno vrijeme se iz lokalnog vremena (Europe/Zagreb)
pretvara u UTC za svaki dan posebno. Tako prelazak na ljetno i zimsko računanje
vremena ne pomiče ponuđene termine.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from django.conf import settings
from django.utils import timezone

from .models import Appointment, DayOff, Service, WorkingHours


def last_bookable_day(now: datetime | None = None) -> date:
    """Zadnji dan za koji se danas može rezervirati."""
    today = timezone.localdate(now or timezone.now())
    return today + timedelta(days=settings.BOOKING_MAX_DAYS_AHEAD)


def free_slots(service: Service, day: date, *, now: datetime | None = None) -> list[datetime]:
    """Vraća početke slobodnih termina za uslugu na zadani dan, uzlazno, u UTC-u.

    Termin je slobodan ako cijelim trajanjem stane u radno vrijeme, ne
    preklapa se ni s jednim rezerviranim terminom i ne počinje prerano
    (``BOOKING_MIN_LEAD_MINUTES`` od sada).
    """
    now = now or timezone.now()
    today = timezone.localdate(now)
    if day < today or day > last_bookable_day(now):
        return []
    if DayOff.objects.filter(date=day).exists():
        return []

    intervals = [
        (_to_utc(day, hours.opens), _to_utc(day, hours.closes))
        for hours in WorkingHours.objects.filter(weekday=day.weekday())
    ]
    if not intervals:
        return []

    day_start = min(start for start, _ in intervals)
    day_end = max(end for _, end in intervals)
    busy = list(
        Appointment.objects.filter(
            status=Appointment.Status.BOOKED,
            starts_at__lt=day_end,
            ends_at__gt=day_start,
        ).values_list("starts_at", "ends_at")
    )

    duration = timedelta(minutes=service.duration_minutes)
    step = timedelta(minutes=settings.BOOKING_SLOT_STEP_MINUTES)
    earliest = now + timedelta(minutes=settings.BOOKING_MIN_LEAD_MINUTES)

    slots = []
    for opens, closes in intervals:
        start = opens
        while start + duration <= closes:
            end = start + duration
            if start >= earliest and not any(
                start < busy_end and busy_start < end for busy_start, busy_end in busy
            ):
                slots.append(start)
            start += step
    return sorted(slots)


def _to_utc(day: date, time) -> datetime:
    local = datetime.combine(day, time, tzinfo=timezone.get_current_timezone())
    return local.astimezone(UTC)
