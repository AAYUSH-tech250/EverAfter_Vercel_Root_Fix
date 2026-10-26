from django.contrib import admin

from .models import Event, Guest, Wedding


@admin.register(Wedding)
class WeddingAdmin(admin.ModelAdmin):
    list_display = ("couple_names", "wedding_date", "venue_name")


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("name", "starts_at", "venue")


@admin.register(Guest)
class GuestAdmin(admin.ModelAdmin):
    list_display = ("name", "phone", "side", "status", "members_coming", "arrival_datetime", "needs_pickup")
    list_filter = ("status", "side", "needs_pickup", "needs_stay")
    search_fields = ("name", "phone")
