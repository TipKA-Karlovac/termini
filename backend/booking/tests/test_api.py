import os
from datetime import timedelta

import pytest
from django.core import mail
from django.db import IntegrityError, connection, transaction
from rest_framework.test import APIClient

from booking import services
from booking.models import Appointment, Service

from .conftest import MONDAY, local

pytestmark = pytest.mark.django_db


def book(client, data, **changes):
    return client.post("/api/appointments/", {**data, **changes}, format="json")


# --- javni dio: usluge i termini ---------------------------------------------


def test_config(client, now):
    body = client.get("/api/config/").json()
    assert body == {
        "business_name": "Salon Test",
        "time_zone": "Europe/Zagreb",
        "today": "2026-03-02",
        "last_bookable_day": "2026-04-01",
        "cancel_until_hours": 2,
    }


def test_services_list_only_active_ones(client, haircut, colouring):
    colouring.active = False
    colouring.save()
    body = client.get("/api/services/").json()
    assert body == [
        {
            "id": haircut.pk,
            "name": "Šišanje",
            "description": "",
            "duration_minutes": 30,
            "price": "15.00",
        }
    ]


def test_slots(client, haircut, working_week, now):
    response = client.get("/api/slots/", {"service": haircut.pk, "date": "2026-03-02"})
    assert response.status_code == 200
    body = response.json()
    assert body["date"] == "2026-03-02"
    assert len(body["slots"]) == 30
    assert body["slots"][0] == "2026-03-02T07:00:00Z"  # 8:00 po lokalnom vremenu


@pytest.mark.parametrize(
    "params",
    [
        {},
        {"service": 1},
        {"date": "2026-03-02"},
        {"service": 999, "date": "2026-03-02"},
        {"service": 1, "date": "2.3.2026."},
    ],
)
def test_slots_reject_bad_parameters(client, haircut, params):
    assert client.get("/api/slots/", params).status_code == 400


def test_slots_do_not_offer_inactive_services(client, haircut, working_week, now):
    haircut.active = False
    haircut.save()
    response = client.get("/api/slots/", {"service": haircut.pk, "date": "2026-03-02"})
    assert response.status_code == 400


# --- rezervacija -------------------------------------------------------------


def test_booking_creates_appointment_and_sends_confirmation(
    client, customer_data, working_week, now
):
    response = book(client, customer_data)
    assert response.status_code == 201, response.content

    appointment = Appointment.objects.get()
    assert appointment.starts_at == local(2, 9)
    assert appointment.ends_at == local(2, 9, 30)
    assert appointment.status == Appointment.Status.BOOKED
    assert appointment.customer_name == "Ana Anić"

    assert response.json() == {
        "service": "Šišanje",
        "duration_minutes": 30,
        "price": "15.00",
        "starts_at": "2026-03-02T09:00:00+01:00",
        "ends_at": "2026-03-02T09:30:00+01:00",
        "customer_name": "Ana Anić",
        "status": "booked",
        "can_cancel": True,
    }

    assert len(mail.outbox) == 1
    message = mail.outbox[0]
    assert message.to == ["ana@example.com"]
    assert "02.03.2026. u 09:00" in message.subject
    assert f"https://termini.test/otkazi/{appointment.cancel_token}" in message.body


def test_booking_response_never_contains_the_cancel_token(client, customer_data, working_week, now):
    response = book(client, customer_data)
    assert Appointment.objects.get().cancel_token not in response.content.decode()


def test_same_slot_cannot_be_booked_twice(client, customer_data, working_week, now):
    assert book(client, customer_data).status_code == 201
    response = book(client, customer_data, customer_name="Iva Ivić")
    assert response.status_code == 409
    assert "više nije slobodan" in response.json()["detail"]
    assert Appointment.objects.count() == 1
    assert len(mail.outbox) == 1


def test_overlapping_slot_cannot_be_booked(client, customer_data, working_week, now):
    assert book(client, customer_data).status_code == 201
    response = book(client, customer_data, starts_at=local(2, 9, 15).isoformat())
    assert response.status_code == 409


@pytest.mark.parametrize(
    "starts_at",
    [
        local(2, 9, 5),  # nije na koraku od 15 min
        local(2, 7),  # prije otvaranja
        local(2, 11, 45),  # ne stane do 12:00
        local(2, 12, 30),  # u pauzi
        local(2, 7, 30),  # prerano i prije otvaranja
        local(7, 9),  # subota
        local(28, 9, month=2),  # prošlost
        local(2, 9, month=5),  # predaleko
    ],
)
def test_only_offered_slots_can_be_booked(client, customer_data, working_week, now, starts_at):
    response = book(client, customer_data, starts_at=starts_at.isoformat())
    assert response.status_code == 409
    assert not Appointment.objects.exists()


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("customer_name", ""),
        ("customer_name", "A"),
        ("customer_name", "x" * 81),
        ("customer_phone", ""),
        ("customer_phone", "nemam"),
        ("customer_phone", "12"),
        ("customer_email", ""),
        ("customer_email", "ana.example.com"),
        ("note", "x" * 301),
        ("service", 999),
        ("service", None),
        ("starts_at", "sutra u 9"),
        ("starts_at", None),
    ],
)
def test_booking_rejects_bad_input(client, customer_data, working_week, now, field, value):
    response = book(client, customer_data, **{field: value})
    assert response.status_code == 400
    assert field in response.json()
    assert not Appointment.objects.exists()
    assert mail.outbox == []


def test_booking_an_inactive_service_is_rejected(client, customer_data, working_week, now):
    Service.objects.update(active=False)
    assert book(client, customer_data).status_code == 400


def test_booking_survives_a_broken_mail_server(
    client, customer_data, working_week, now, monkeypatch
):
    def broken(*args, **kwargs):
        raise OSError("poslužitelj e-pošte ne odgovara")

    monkeypatch.setattr("booking.emails.send_mail", broken)
    assert book(client, customer_data).status_code == 201
    assert Appointment.objects.count() == 1


def test_booking_is_rate_limited(client, customer_data, working_week, now, settings):
    settings.REST_FRAMEWORK = {
        **settings.REST_FRAMEWORK,
        "DEFAULT_THROTTLE_RATES": {"booking": "2/hour", "login": "1000/hour"},
    }
    from rest_framework.throttling import ScopedRateThrottle

    ScopedRateThrottle.THROTTLE_RATES = settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]
    try:
        statuses = [book(client, customer_data, customer_email="").status_code for _ in range(3)]
    finally:
        del ScopedRateThrottle.THROTTLE_RATES
    assert statuses == [400, 400, 429]


@pytest.mark.skipif(
    connection.vendor != "postgresql", reason="ograničenje postoji samo na PostgreSQL-u"
)
def test_database_itself_rejects_overlapping_appointments(haircut):
    """Zaobilazi provjeru u kodu i upisuje izravno: baza mora odbiti preklapanje."""

    def insert(starts_at, status=Appointment.Status.BOOKED):
        return Appointment.objects.create(
            service=haircut,
            starts_at=starts_at,
            ends_at=starts_at + timedelta(minutes=30),
            customer_name="Ana Anić",
            customer_phone="091 234 5678",
            customer_email="ana@example.com",
            status=status,
        )

    insert(local(2, 9))
    insert(local(2, 9, 30))  # nastavlja se bez preklapanja
    insert(local(2, 9, 15), status=Appointment.Status.CANCELLED)  # otkazani ne smetaju
    with pytest.raises(IntegrityError), transaction.atomic():
        insert(local(2, 9, 15))


def test_ci_runs_on_the_database_it_claims():
    """U CI-ju posao „postgres” ne smije potiho raditi na SQLiteu i preskočiti test iznad."""
    expected = os.environ.get("EXPECTED_DATABASE")
    if not expected:
        pytest.skip("EXPECTED_DATABASE nije postavljen (lokalno pokretanje)")
    assert connection.vendor == expected


# --- otkazivanje poveznicom --------------------------------------------------


@pytest.fixture
def appointment(client, customer_data, working_week, now):
    assert book(client, customer_data).status_code == 201
    mail.outbox.clear()
    return Appointment.objects.get()


def test_cancel_link_shows_the_appointment(client, appointment):
    body = client.get(f"/api/appointments/cancel/{appointment.cancel_token}/").json()
    assert body["service"] == "Šišanje"
    assert body["status"] == "booked"
    assert body["can_cancel"] is True


def test_customer_cancels_and_slot_becomes_free_again(client, appointment, customer_data):
    response = client.post(f"/api/appointments/cancel/{appointment.cancel_token}/")
    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"
    assert response.json()["can_cancel"] is False

    appointment.refresh_from_db()
    assert appointment.status == Appointment.Status.CANCELLED
    assert appointment.cancelled_at == MONDAY

    assert len(mail.outbox) == 1
    assert "na Vaš zahtjev" in mail.outbox[0].body

    assert book(client, customer_data, customer_name="Iva Ivić").status_code == 201


def test_cancelling_twice_is_refused(client, appointment):
    url = f"/api/appointments/cancel/{appointment.cancel_token}/"
    assert client.post(url).status_code == 200
    response = client.post(url)
    assert response.status_code == 409
    assert "već otkazan" in response.json()["detail"]
    assert len(mail.outbox) == 1


def test_customer_cannot_cancel_after_the_deadline(client, appointment, monkeypatch):
    # Termin je u 9:00, rok je 2 h prije; u 7:01 je prekasno.
    late = MONDAY.replace(minute=1)
    monkeypatch.setattr("django.utils.timezone.now", lambda: late)
    url = f"/api/appointments/cancel/{appointment.cancel_token}/"
    assert client.get(url).json()["can_cancel"] is False
    response = client.post(url)
    assert response.status_code == 409
    assert "najkasnije 2 h prije" in response.json()["detail"]
    appointment.refresh_from_db()
    assert appointment.status == Appointment.Status.BOOKED


def test_unknown_cancel_token_is_not_found(client, appointment):
    assert client.get("/api/appointments/cancel/nepostojeci-token/").status_code == 404
    assert client.post("/api/appointments/cancel/nepostojeci-token/").status_code == 404
    appointment.refresh_from_db()
    assert appointment.status == Appointment.Status.BOOKED


def test_cancel_tokens_are_long_and_unique(haircut, working_week, now):
    first = services.book(
        service=haircut,
        starts_at=local(2, 9),
        customer_name="Ana Anić",
        customer_phone="091 234 5678",
        customer_email="ana@example.com",
    )
    second = services.book(
        service=haircut,
        starts_at=local(2, 10),
        customer_name="Iva Ivić",
        customer_phone="091 234 5679",
        customer_email="iva@example.com",
    )
    assert first.cancel_token != second.cancel_token
    assert len(first.cancel_token) >= 43  # 32 slučajna bajta


# --- prijava vlasnika --------------------------------------------------------


def login(client, username="vlasnik", password="tajna-lozinka"):
    return client.post(
        "/api/auth/login/", {"username": username, "password": password}, format="json"
    )


def test_owner_logs_in_and_out(client, owner):
    assert client.get("/api/auth/me/").json() == {"authenticated": False, "username": ""}

    response = login(client)
    assert response.status_code == 200
    assert response.json() == {"authenticated": True, "username": "vlasnik"}
    assert client.get("/api/auth/me/").json() == {"authenticated": True, "username": "vlasnik"}

    assert client.post("/api/auth/logout/").status_code == 200
    assert client.get("/api/auth/me/").json() == {"authenticated": False, "username": ""}


def test_wrong_password_and_unknown_user_get_the_same_answer(client, owner):
    wrong = login(client, password="kriva")
    unknown = login(client, username="nitko")
    assert wrong.status_code == unknown.status_code == 400
    assert wrong.json() == unknown.json()


def test_ordinary_user_cannot_log_in_as_owner(client, django_user_model):
    django_user_model.objects.create_user("gost", password="tajna-lozinka")
    assert login(client, username="gost").status_code == 400
    assert client.get("/api/auth/me/").json()["authenticated"] is False


def test_login_requires_a_csrf_token(owner):
    strict = APIClient(enforce_csrf_checks=True)
    data = {"username": "vlasnik", "password": "tajna-lozinka"}
    assert strict.post("/api/auth/login/", data, format="json").status_code == 403

    strict.get("/api/auth/me/")  # postavlja CSRF kolačić
    token = strict.cookies["csrftoken"].value
    response = strict.post("/api/auth/login/", data, format="json", HTTP_X_CSRFTOKEN=token)
    assert response.status_code == 200


def test_login_works_from_the_frontend_origin_only(owner):
    # Web sučelje smije biti na drugoj adresi od API-ja (Vite u razvoju).
    strict = APIClient(enforce_csrf_checks=True)
    strict.get("/api/auth/me/")
    token = strict.cookies["csrftoken"].value
    data = {"username": "vlasnik", "password": "tajna-lozinka"}

    def post(origin):
        return strict.post(
            "/api/auth/login/", data, format="json", HTTP_X_CSRFTOKEN=token, HTTP_ORIGIN=origin
        )

    assert post("https://zlonamjerna-stranica.test").status_code == 403
    assert post("https://termini.test").status_code == 200


def test_frontend_url_is_a_trusted_origin_by_default():
    from config import settings as base

    assert base.FRONTEND_URL in base.CSRF_TRUSTED_ORIGINS


# --- dio za vlasnika ---------------------------------------------------------


@pytest.mark.parametrize(
    ("method", "url"),
    [
        ("get", "/api/owner/appointments/"),
        ("post", "/api/owner/appointments/1/cancel/"),
    ],
)
def test_owner_endpoints_are_closed_to_everyone_else(client, django_user_model, method, url):
    assert getattr(client, method)(url).status_code == 403

    django_user_model.objects.create_user("gost", password="tajna-lozinka")
    client.login(username="gost", password="tajna-lozinka")
    assert getattr(client, method)(url).status_code == 403


def test_owner_sees_the_day_with_customer_contacts(client, owner, appointment):
    client.force_login(owner)
    body = client.get("/api/owner/appointments/", {"date": "2026-03-02"}).json()
    assert len(body) == 1
    assert body[0]["id"] == appointment.pk
    assert body[0]["customer_phone"] == "091 234 5678"
    assert body[0]["customer_email"] == "ana@example.com"
    assert "cancel_token" not in body[0]

    assert client.get("/api/owner/appointments/", {"date": "2026-03-03"}).json() == []


def test_owner_list_defaults_to_today(client, owner, appointment):
    client.force_login(owner)
    assert len(client.get("/api/owner/appointments/").json()) == 1


def test_owner_list_uses_the_local_day(client, owner, haircut, working_week, now):
    # 23:30 po lokalnom vremenu je 22:30 UTC – mora ostati u istom lokalnom danu.
    Appointment.objects.create(
        service=haircut,
        starts_at=local(2, 23, 30),
        ends_at=local(3, 0, 0),
        customer_name="Kasni Klijent",
        customer_phone="091 234 5678",
        customer_email="kasni@example.com",
    )
    client.force_login(owner)
    assert len(client.get("/api/owner/appointments/", {"date": "2026-03-02"}).json()) == 1
    assert client.get("/api/owner/appointments/", {"date": "2026-03-03"}).json() == []


def test_owner_can_cancel_even_after_the_customer_deadline(client, owner, appointment, monkeypatch):
    late = MONDAY.replace(hour=8, minute=30)
    monkeypatch.setattr("django.utils.timezone.now", lambda: late)
    client.force_login(owner)

    response = client.post(f"/api/owner/appointments/{appointment.pk}/cancel/")
    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"
    assert "morali smo otkazati" in mail.outbox[0].body

    assert client.post(f"/api/owner/appointments/{appointment.pk}/cancel/").status_code == 409


def test_owner_cancel_of_unknown_appointment_is_not_found(client, owner):
    client.force_login(owner)
    assert client.post("/api/owner/appointments/999/cancel/").status_code == 404
