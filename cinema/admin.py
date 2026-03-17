from django.contrib import admin
from .models import Room, Seat, Session, Ticket


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ("id", "name")


@admin.register(Seat)
class SeatAdmin(admin.ModelAdmin):
    list_display = ("id", "room", "row", "number")
    list_filter = ("room", "row")


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ("id", "movie", "room", "starts_at")
    list_filter = ("room", "movie")


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "session", "seat", "created_at")
    list_filter = ("session",)