from rest_framework import serializers

from . import services
from .models import Appointment, Service


class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = ["id", "name", "description", "duration_minutes", "price"]


class SlotsQuerySerializer(serializers.Serializer):
    service = serializers.PrimaryKeyRelatedField(queryset=Service.objects.filter(active=True))
    date = serializers.DateField()


class BookingSerializer(serializers.ModelSerializer):
    """Ulazni podaci javnog obrasca za rezervaciju."""

    service = serializers.PrimaryKeyRelatedField(queryset=Service.objects.filter(active=True))

    class Meta:
        model = Appointment
        fields = [
            "service",
            "starts_at",
            "customer_name",
            "customer_phone",
            "customer_email",
            "note",
        ]

    def validate_customer_name(self, value):
        value = " ".join(value.split())
        if len(value) < 2:
            raise serializers.ValidationError("Upišite ime i prezime.")
        return value


class PublicAppointmentSerializer(serializers.ModelSerializer):
    """Ono što klijent smije vidjeti o svom terminu. Bez tajne poveznice i kontakata."""

    service = serializers.CharField(source="service.name")
    duration_minutes = serializers.IntegerField(source="service.duration_minutes")
    price = serializers.DecimalField(source="service.price", max_digits=7, decimal_places=2)
    can_cancel = serializers.SerializerMethodField()

    class Meta:
        model = Appointment
        fields = [
            "service",
            "duration_minutes",
            "price",
            "starts_at",
            "ends_at",
            "customer_name",
            "status",
            "can_cancel",
        ]

    def get_can_cancel(self, appointment) -> bool:
        return services.can_cancel(appointment)


class OwnerAppointmentSerializer(serializers.ModelSerializer):
    service = serializers.CharField(source="service.name")
    duration_minutes = serializers.IntegerField(source="service.duration_minutes")

    class Meta:
        model = Appointment
        fields = [
            "id",
            "service",
            "duration_minutes",
            "starts_at",
            "ends_at",
            "customer_name",
            "customer_phone",
            "customer_email",
            "note",
            "status",
            "created_at",
        ]


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(max_length=128, trim_whitespace=False)
