from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("login/", auth_views.LoginView.as_view(template_name="core/login.html"), name="login"),
    path("signup/", views.signup, name="signup"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),

    path("dashboard/", views.dashboard, name="dashboard"),
    path("attendance/", views.attendance_view, name="attendance_view"),
    path("my-wedding/", views.guest_portal, name="guest_portal"),

    path("guests/", views.guest_list, name="guest_list"),
    path("guests/add/", views.guest_add, name="guest_add"),
    path("guests/bulk/", views.guest_bulk, name="guest_bulk"),
    path("guests/export/", views.guest_export, name="guest_export"),
    path("guests/<int:pk>/", views.guest_edit, name="guest_edit"),
    path("guests/<int:pk>/delete/", views.guest_delete, name="guest_delete"),
    path("guests/<int:pk>/send/", views.guest_send, name="guest_send"),

    path("arrivals/", views.logistics, name="logistics"),
    path("arrivals/export/", views.logistics_export, name="logistics_export"),

    path("programs/", views.program_list, name="program_list"),
    path("programs/add/", views.program_add, name="program_add"),
    path("programs/<int:pk>/", views.program_edit, name="program_edit"),
    path("programs/<int:pk>/delete/", views.program_delete, name="program_delete"),

    path("settings/", views.wedding_settings, name="wedding_settings"),

    # the personal invitation link that is sent to each guest
    path("r/<uuid:token>/", views.rsvp, name="rsvp"),
]
