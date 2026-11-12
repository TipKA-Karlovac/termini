"""Poslovna pravila: rezervacija i otkazivanje termina."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

from . import emails
from .models import Appointment, Service
from .slots import free_slots

logger = logging.getLogger(__name__)


class SlotUnavailable(Exception):
    """Traženi termin nije (ili više nije) slobodan."""


class CancellationNotAllowed(Exception):
    """Termin se više ne može otkazati."""


def book(
    *,
    service: Service,
    starts_at: datetime,
    customer_name: str,
    customer_phone: str,
    customer_email: str,
    note: str = "",
    now: datetime | None = None,
) -> Appointment:
    """Rezervira termin ili baca :class:`SlotUnavailable`.

    Dvije obrane od dvostruke rezervacije:

    1. provjera slobodnih termina unutar transakcije;
    2. na PostgreSQL-u isključujuće ograničenje u bazi, koje hvata i slučaj
       kad dva zahtjeva istodobno prođu prvu provjeru.
    """
    starts_at = starts_at.astimezone(UTC)
    day = timezone.localdate(starts_at)
    try:
        with transaction.atomic():
            if starts_at not in free_slots(service, day, now=now):
                raise SlotUnavailable
            appointment = Appointment.objects.create(
                service=service,
                starts_at=starts_at,
                ends_at=starts_at + timedelta(minutes=service.duration_minutes),
                customer_name=customer_name,
                customer_phone=customer_phone,
                customer_email=customer_email,
                note=note,
            )
    except IntegrityError as exc:
        raise SlotUnavailable from exc

    _send(emails.send_confirmation, appointment)
    return appointment


def can_cancel(appointment: Appointment, *, now: datetime | None = None) -> bool:
    """Klijent smije otkazati rezervirani termin do određenog broja sati prije početka."""
    now = now or timezone.now()
    deadline = appointment.starts_at - timedelta(hours=settings.BOOKING_CANCEL_UNTIL_HOURS)
    return appointment.status == Appointment.Status.BOOKED and now <= deadline


def cancel(
    appointment: Appointment, *, by_owner: bool = False, now: datetime | None = None
) -> Appointment:
    """Otkazuje termin. Vlasnik može otkazati bilo kad, klijent samo do roka."""
    now = now or timezone.now()
    with transaction.atomic():
        appointment = Appointment.objects.select_for_update().get(pk=appointment.pk)
        if appointment.status != Appointment.Status.BOOKED:
            raise CancellationNotAllowed("Termin je već otkazan.")
        if not by_owner and not can_cancel(appointment, now=now):
            raise CancellationNotAllowed(
                "Termin se može otkazati najkasnije "
                f"{settings.BOOKING_CANCEL_UNTIL_HOURS} h prije početka. Nazovite nas."
            )
        appointment.status = Appointment.Status.CANCELLED
        appointment.cancelled_at = now
        appointment.save(update_fields=["status", "cancelled_at"])

    _send(emails.send_cancellation, appointment, by_owner=by_owner)
    return appointment


def _send(function, appointment: Appointment, **kwargs) -> None:
    # Rezervacija je već spremljena; kvar na poslužitelju e-pošte ne smije je
    # poništiti ni klijentu prikazati pogrešku.
    try:
        function(appointment, **kwargs)
    except Exception:
        logger.exception("Slanje e-pošte za termin %s nije uspjelo.", appointment.pk)
