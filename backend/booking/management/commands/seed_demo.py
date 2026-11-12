from datetime import time
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from booking.models import Service, WorkingHours

SERVICES = [
    ("Šišanje", "Pranje, šišanje i oblikovanje", 30, "15.00"),
    ("Šišanje i brada", "Šišanje uz uređivanje brade", 45, "22.00"),
    ("Bojanje", "Bojanje cijele dužine", 90, "45.00"),
    ("Dječje šišanje", "Za djecu do 12 godina", 20, "10.00"),
]

# ponedjeljak–petak dvokratno, subota jednokratno, nedjelja zatvoreno
HOURS = [
    *[(day, time(8), time(12)) for day in range(5)],
    *[(day, time(14), time(18)) for day in range(5)],
    (5, time(8), time(13)),
]


class Command(BaseCommand):
    help = "Puni bazu primjerom salona: usluge, radno vrijeme i (po želji) korisnik vlasnika."

    def add_arguments(self, parser):
        parser.add_argument(
            "--owner",
            metavar="KORISNIK",
            help="Stvori korisnika vlasnika s tim imenom. Lozinku zatim postavite naredbom "
            "'manage.py changepassword KORISNIK'.",
        )

    def handle(self, *args, **options):
        for position, (name, description, minutes, price) in enumerate(SERVICES):
            Service.objects.update_or_create(
                name=name,
                defaults={
                    "description": description,
                    "duration_minutes": minutes,
                    "price": Decimal(price),
                    "position": position,
                },
            )
        for weekday, opens, closes in HOURS:
            WorkingHours.objects.get_or_create(weekday=weekday, opens=opens, closes=closes)
        self.stdout.write(self.style.SUCCESS("Usluge i radno vrijeme su upisani."))

        if options["owner"]:
            user, created = get_user_model().objects.get_or_create(
                username=options["owner"], defaults={"is_staff": True, "is_superuser": True}
            )
            if created:
                user.set_unusable_password()
                user.save()
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Korisnik '{user.username}' je stvoren bez lozinke. Postavite je: "
                        f"python manage.py changepassword {user.username}"
                    )
                )
            else:
                self.stdout.write(f"Korisnik '{user.username}' već postoji.")
