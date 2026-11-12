"""E-pošta klijentu: potvrda rezervacije i obavijest o otkazivanju."""

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from .models import Appointment


def _when(appointment: Appointment) -> str:
    return timezone.localtime(appointment.starts_at).strftime("%d.%m.%Y. u %H:%M")


def cancel_url(appointment: Appointment) -> str:
    return f"{settings.FRONTEND_URL}/otkazi/{appointment.cancel_token}"


def send_confirmation(appointment: Appointment) -> None:
    body = (
        f"Poštovani/a {appointment.customer_name},\n\n"
        f"Vaš termin je rezerviran.\n\n"
        f"Usluga: {appointment.service.name}\n"
        f"Vrijeme: {_when(appointment)}\n"
        f"Trajanje: {appointment.service.duration_minutes} min\n\n"
        f"Ako ne možete doći, termin možete otkazati najkasnije "
        f"{settings.BOOKING_CANCEL_UNTIL_HOURS} h prije početka na ovoj poveznici:\n"
        f"{cancel_url(appointment)}\n\n"
        f"{settings.BUSINESS_NAME}"
    )
    send_mail(
        subject=f"Potvrda termina – {_when(appointment)}",
        message=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[appointment.customer_email],
    )


def send_cancellation(appointment: Appointment, *, by_owner: bool = False) -> None:
    reason = (
        "Nažalost, morali smo otkazati Vaš termin. Ispričavamo se i molimo Vas da rezervirate novi."
        if by_owner
        else "Vaš termin je otkazan na Vaš zahtjev."
    )
    body = (
        f"Poštovani/a {appointment.customer_name},\n\n"
        f"{reason}\n\n"
        f"Usluga: {appointment.service.name}\n"
        f"Vrijeme: {_when(appointment)}\n\n"
        f"Novi termin možete rezervirati ovdje: {settings.FRONTEND_URL}\n\n"
        f"{settings.BUSINESS_NAME}"
    )
    send_mail(
        subject=f"Termin otkazan – {_when(appointment)}",
        message=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[appointment.customer_email],
    )
