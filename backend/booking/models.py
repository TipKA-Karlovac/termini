import secrets
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db import models
from django.db.models import F, Q


class Service(models.Model):
    """Usluga koju klijent rezervira, npr. „Šišanje – 30 min”."""

    name = models.CharField("naziv", max_length=80)
    description = models.CharField("opis", max_length=200, blank=True)
    duration_minutes = models.PositiveSmallIntegerField(
        "trajanje (min)",
        validators=[MinValueValidator(5), MaxValueValidator(480)],
    )
    price = models.DecimalField(
        "cijena (EUR)",
        max_digits=7,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
    )
    active = models.BooleanField(
        "aktivna",
        default=True,
        help_text="Neaktivna usluga se ne nudi klijentima, a postojeći termini ostaju.",
    )
    position = models.PositiveSmallIntegerField("redoslijed", default=0)

    class Meta:
        ordering = ["position", "name"]
        verbose_name = "usluga"
        verbose_name_plural = "usluge"

    def __str__(self):
        return f"{self.name} ({self.duration_minutes} min)"


class WorkingHours(models.Model):
    """Jedan neprekinuti dio radnog dana. Dvokratno radno vrijeme su dva zapisa."""

    class Weekday(models.IntegerChoices):
        MONDAY = 0, "ponedjeljak"
        TUESDAY = 1, "utorak"
        WEDNESDAY = 2, "srijeda"
        THURSDAY = 3, "četvrtak"
        FRIDAY = 4, "petak"
        SATURDAY = 5, "subota"
        SUNDAY = 6, "nedjelja"

    weekday = models.PositiveSmallIntegerField("dan", choices=Weekday.choices)
    opens = models.TimeField("od")
    closes = models.TimeField("do")

    class Meta:
        ordering = ["weekday", "opens"]
        verbose_name = "radno vrijeme"
        verbose_name_plural = "radno vrijeme"
        constraints = [
            models.CheckConstraint(
                condition=Q(opens__lt=F("closes")),
                name="working_hours_opens_before_closes",
            ),
        ]

    def __str__(self):
        return f"{self.get_weekday_display()} {self.opens:%H:%M}–{self.closes:%H:%M}"

    def clean(self):
        if self.opens is None or self.closes is None or self.weekday is None:
            return
        if self.opens >= self.closes:
            raise ValidationError("Početak radnog vremena mora biti prije kraja.")
        overlapping = WorkingHours.objects.filter(
            weekday=self.weekday, opens__lt=self.closes, closes__gt=self.opens
        ).exclude(pk=self.pk)
        if overlapping.exists():
            raise ValidationError("Za taj dan već postoji radno vrijeme koje se preklapa s ovim.")


class DayOff(models.Model):
    """Dan kad se ne radi: blagdan, godišnji odmor i slično."""

    date = models.DateField("datum", unique=True)
    reason = models.CharField("razlog", max_length=100, blank=True)

    class Meta:
        ordering = ["date"]
        verbose_name = "neradni dan"
        verbose_name_plural = "neradni dani"

    def __str__(self):
        return f"{self.date:%d.%m.%Y.} {self.reason}".strip()


def _new_cancel_token() -> str:
    return secrets.token_urlsafe(32)


class Appointment(models.Model):
    """Rezervirani termin.

    Otkazani termini se ne brišu – ostaju kao trag, a vrijeme oslobađaju jer
    se pri traženju slobodnih termina gledaju samo oni sa statusom BOOKED.
    """

    class Status(models.TextChoices):
        BOOKED = "booked", "rezervirano"
        CANCELLED = "cancelled", "otkazano"

    service = models.ForeignKey(
        Service, verbose_name="usluga", on_delete=models.PROTECT, related_name="appointments"
    )
    starts_at = models.DateTimeField("početak")
    ends_at = models.DateTimeField("kraj")

    customer_name = models.CharField("ime i prezime", max_length=80)
    customer_phone = models.CharField(
        "telefon",
        max_length=30,
        validators=[
            RegexValidator(
                r"^\+?[0-9][0-9 /()-]{5,28}$",
                "Upišite telefonski broj, npr. 091 234 5678.",
            )
        ],
    )
    customer_email = models.EmailField("e-pošta")
    note = models.CharField("napomena", max_length=300, blank=True)

    status = models.CharField(
        "status", max_length=10, choices=Status.choices, default=Status.BOOKED
    )
    # Tajna poveznica iz e-pošte kojom klijent otkazuje bez prijave.
    cancel_token = models.CharField(
        max_length=64, unique=True, default=_new_cancel_token, editable=False
    )
    cancelled_at = models.DateTimeField("otkazano", null=True, blank=True)
    created_at = models.DateTimeField("zaprimljeno", auto_now_add=True)

    class Meta:
        ordering = ["starts_at"]
        verbose_name = "termin"
        verbose_name_plural = "termini"
        indexes = [models.Index(fields=["status", "starts_at"])]
        constraints = [
            models.CheckConstraint(
                condition=Q(starts_at__lt=F("ends_at")),
                name="appointment_starts_before_ends",
            ),
            # Na PostgreSQL-u migracija 0002 dodaje i isključujuće ograničenje
            # koje bazi zabranjuje dva rezervirana termina koji se preklapaju.
        ]

    def __str__(self):
        return f"{self.starts_at:%d.%m.%Y. %H:%M} {self.customer_name}"
