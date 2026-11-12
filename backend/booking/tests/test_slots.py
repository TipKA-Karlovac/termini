from datetime import date, time, timedelta

import pytest
from django.core.exceptions import ValidationError

from booking.models import Appointment, DayOff, WorkingHours
from booking.slots import free_slots

from .conftest import MONDAY, local

pytestmark = pytest.mark.django_db

DAY = date(2026, 3, 2)  # ponedjeljak


def book(service, starts_at, status=Appointment.Status.BOOKED):
    return Appointment.objects.create(
        service=service,
        starts_at=starts_at,
        ends_at=starts_at + timedelta(minutes=service.duration_minutes),
        customer_name="Ana Anić",
        customer_phone="091 234 5678",
        customer_email="ana@example.com",
        status=status,
    )


def test_slots_cover_both_parts_of_a_split_day(haircut, working_week, now):
    slots = free_slots(haircut, DAY)
    # 8:00–12:00 i 14:00–18:00, korak 15 min, usluga 30 min:
    # zadnji početak je 11:30 odnosno 17:30 → 15 + 15 termina.
    assert len(slots) == 30
    assert slots[0] == local(2, 8)
    assert slots[14] == local(2, 11, 30)
    assert slots[15] == local(2, 14)
    assert slots[-1] == local(2, 17, 30)
    assert slots == sorted(slots)


def test_service_must_fit_before_closing(colouring, working_week, now):
    slots = free_slots(colouring, DAY)
    # 90 min: zadnji početak je 10:30 odnosno 16:30.
    assert local(2, 10, 30) in slots
    assert local(2, 10, 45) not in slots
    assert slots[-1] == local(2, 16, 30)


def test_service_longer_than_the_working_interval_has_no_slots(colouring, now):
    WorkingHours.objects.create(weekday=0, opens=time(8), closes=time(9))
    assert free_slots(colouring, DAY) == []


def test_booked_appointment_blocks_every_overlapping_start(haircut, working_week, now):
    book(haircut, local(2, 9))  # 9:00–9:30
    slots = free_slots(haircut, DAY)
    assert local(2, 8, 30) in slots  # završava točno u 9:00
    assert local(2, 8, 45) not in slots  # zašao bi u 9:00–9:15
    assert local(2, 9) not in slots
    assert local(2, 9, 15) not in slots
    assert local(2, 9, 30) in slots  # počinje točno kad prethodni završi


def test_long_service_cannot_start_into_a_booked_appointment(haircut, colouring, working_week, now):
    book(haircut, local(2, 10))  # 10:00–10:30
    slots = free_slots(colouring, DAY)
    assert local(2, 8, 30) in slots  # 8:30–10:00
    assert local(2, 8, 45) not in slots  # 8:45–10:15
    assert local(2, 10, 30) in slots


def test_cancelled_appointment_frees_the_slot(haircut, working_week, now):
    book(haircut, local(2, 9), status=Appointment.Status.CANCELLED)
    assert local(2, 9) in free_slots(haircut, DAY)


def test_slots_respect_minimum_lead_time(haircut, working_week):
    # U 9:10 uz najmanje 60 min najave prvi mogući početak je 10:15.
    at = MONDAY.replace(hour=9, minute=10)
    slots = free_slots(haircut, DAY, now=at)
    assert slots[0] == local(2, 10, 15)


def test_no_slots_in_the_past(haircut, working_week, now):
    assert free_slots(haircut, date(2026, 2, 27)) == []


def test_no_slots_beyond_the_booking_horizon(haircut, working_week, now):
    assert free_slots(haircut, date(2026, 4, 1)) != []  # 30. dan
    assert free_slots(haircut, date(2026, 4, 2)) == []  # 31. dan


def test_no_slots_on_a_day_without_working_hours(haircut, working_week, now):
    assert free_slots(haircut, date(2026, 3, 7)) == []  # subota


def test_no_slots_on_a_day_off(haircut, working_week, now):
    DayOff.objects.create(date=DAY, reason="Godišnji odmor")
    assert free_slots(haircut, DAY) == []
    assert free_slots(haircut, DAY + timedelta(days=1)) != []


def test_opening_time_stays_local_across_the_daylight_saving_change(haircut, working_week, now):
    # Sat se pomiče u nedjelju 29. 3. 2026. Salon i dalje otvara u 8:00 po
    # lokalnom vremenu, što je u UTC-u sat ranije nego tjedan prije.
    before = free_slots(haircut, date(2026, 3, 27))[0]
    after = free_slots(haircut, date(2026, 3, 30))[0]
    assert before == local(27, 8)
    assert after == local(30, 8)
    assert (before.hour, after.hour) == (7, 6)


def test_working_hours_cannot_overlap_on_the_same_day():
    WorkingHours.objects.create(weekday=0, opens=time(8), closes=time(12))
    with pytest.raises(ValidationError, match="preklapa"):
        WorkingHours(weekday=0, opens=time(11), closes=time(15)).full_clean()
    WorkingHours(weekday=0, opens=time(12), closes=time(15)).full_clean()  # nastavlja se
    WorkingHours(weekday=1, opens=time(11), closes=time(15)).full_clean()  # drugi dan


def test_working_hours_must_open_before_closing():
    with pytest.raises(ValidationError, match="prije kraja"):
        WorkingHours(weekday=0, opens=time(12), closes=time(8)).full_clean()
