from django.urls import path

from . import views

urlpatterns = [
    # javni dio
    path("config/", views.ConfigView.as_view(), name="config"),
    path("services/", views.ServiceListView.as_view(), name="services"),
    path("slots/", views.SlotsView.as_view(), name="slots"),
    path("appointments/", views.BookingView.as_view(), name="book"),
    path("appointments/cancel/<str:token>/", views.CancelView.as_view(), name="cancel"),
    # prijava vlasnika
    path("auth/me/", views.MeView.as_view(), name="me"),
    path("auth/login/", views.LoginView.as_view(), name="login"),
    path("auth/logout/", views.LogoutView.as_view(), name="logout"),
    # dio za vlasnika
    path("owner/appointments/", views.OwnerAppointmentListView.as_view(), name="owner-list"),
    path(
        "owner/appointments/<int:pk>/cancel/",
        views.OwnerCancelView.as_view(),
        name="owner-cancel",
    ),
]
