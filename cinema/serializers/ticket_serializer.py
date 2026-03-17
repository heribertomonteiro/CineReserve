from rest_framework import serializers

from ..models import Ticket


class TicketCreateSerializer(serializers.Serializer):
    session_id = serializers.IntegerField(min_value=1)
    seat_id = serializers.IntegerField(min_value=1)

class MyTicketSerializer(serializers.ModelSerializer):
    session_starts_at = serializers.DateTimeField(source="session.starts_at")
    movie = serializers.StringRelatedField(source="session.movie")
    room = serializers.StringRelatedField(source="session.room")
    seat = serializers.CharField(source="seat.label")

    class Meta:
        model = Ticket
        fields = ( "id", "movie", "room", "seat", "session_starts_at", "created_at")