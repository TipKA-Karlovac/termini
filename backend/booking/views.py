from datetime import UTC, datetime, time, timedelta

from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from rest_framework import status
from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from . import services
from .models import Appointment, Service
from .serializers import (
    BookingSerializer,
    LoginSerializer,
    OwnerAppointmentSerializer,
    PublicAppointmentSerializer,
    ServiceSerializer,
    SlotsQuerySerializer,
)
from .slots import free_slots, last_bookable_day


class PublicView(APIView):
    """Javni dio: bez prijave. Bez sjednice nema ni CSRF napada koji bi imao što ukrasti."""

    authentication_classes = []
    permission_classes = [AllowAny]


# --- javni dio ---------------------------------------------------------------


class ConfigView(PublicView):
    def get(self, request):
        return Response(
            {
                "business_name": settings.BUSINESS_NAME,
                "time_zone": settings.TIME_ZONE,
                "today": timezone.localdate(),
                "last_bookable_day": last_bookable_day(),
                "cancel_until_hours": settings.BOOKING_CANCEL_UNTIL_HOURS,
            }
        )


class ServiceListView(ListAPIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    serializer_class = ServiceSerializer
    queryset = Service.objects.filter(active=True)
    pagination_class = None


class SlotsView(PublicView):
    """Slobodni termini za uslugu na zadani dan. Ne otkriva ništa o tuđim rezervacijama."""

    def get(self, request):
        query = SlotsQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        day = query.validated_data["date"]
        slots = free_slots(query.validated_data["service"], day)
        return Response({"date": day, "slots": slots})


class BookingView(PublicView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "booking"

    def post(self, request):
        serializer = BookingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            appointment = services.book(**serializer.validated_data)
        except services.SlotUnavailable:
            return Response(
                {"detail": "Taj termin više nije slobodan. Odaberite drugi."},
                status=status.HTTP_409_CONFLICT,
            )
        return Response(
            PublicAppointmentSerializer(appointment).data, status=status.HTTP_201_CREATED
        )


class CancelView(PublicView):
    """Otkazivanje tajnom poveznicom iz e-pošte."""

    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "booking"

    def get(self, request, token):
        appointment = get_object_or_404(_with_service(), cancel_token=token)
        return Response(PublicAppointmentSerializer(appointment).data)

    def post(self, request, token):
        appointment = get_object_or_404(_with_service(), cancel_token=token)
        try:
            appointment = services.cancel(appointment)
        except services.CancellationNotAllowed as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        appointment = _with_service().get(pk=appointment.pk)
        return Response(PublicAppointmentSerializer(appointment).data)


# --- prijava vlasnika --------------------------------------------------------


@method_decorator(ensure_csrf_cookie, name="dispatch")
class MeView(APIView):
    """Tko je prijavljen. Usput postavlja CSRF kolačić potreban za prijavu."""

    permission_classes = [AllowAny]

    def get(self, request):
        user = request.user
        is_owner = user.is_authenticated and user.is_staff
        return Response({"authenticated": is_owner, "username": user.username if is_owner else ""})


@method_decorator(csrf_protect, name="dispatch")
class LoginView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = authenticate(request, **serializer.validated_data)
        # Ista poruka za krivu lozinku i za korisnika koji nije vlasnik, da se
        # iz odgovora ne može saznati koja korisnička imena postoje.
        if user is None or not user.is_staff:
            return Response(
                {"detail": "Pogrešno korisničko ime ili lozinka."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        login(request, user)
        return Response({"authenticated": True, "username": user.username})


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        logout(request)
        return Response({"authenticated": False, "username": ""})


# --- dio za vlasnika ---------------------------------------------------------


class OwnerAppointmentListView(ListAPIView):
    """Termini jednog dana (zadano: danas), s kontaktima klijenata."""

    permission_classes = [IsAdminUser]
    serializer_class = OwnerAppointmentSerializer
    pagination_class = None

    def get_queryset(self):
        day = self.request.query_params.get("date")
        try:
            day = datetime.strptime(day, "%Y-%m-%d").date() if day else timezone.localdate()
        except ValueError:
            day = timezone.localdate()
        zone = timezone.get_current_timezone()
        start = datetime.combine(day, time.min, tzinfo=zone).astimezone(UTC)
        end = datetime.combine(day + timedelta(days=1), time.min, tzinfo=zone).astimezone(UTC)
        return _with_service().filter(starts_at__gte=start, starts_at__lt=end)


class OwnerCancelView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, pk):
        appointment = get_object_or_404(_with_service(), pk=pk)
        try:
            appointment = services.cancel(appointment, by_owner=True)
        except services.CancellationNotAllowed as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        appointment = _with_service().get(pk=appointment.pk)
        return Response(OwnerAppointmentSerializer(appointment).data)


def _with_service():
    return Appointment.objects.select_related("service")
