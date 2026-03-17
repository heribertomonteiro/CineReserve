from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.shortcuts import get_object_or_404
from django.core.cache import cache
from drf_spectacular.utils import extend_schema
from .models import Session, Seat
from .serializers.seat_serializer import SeatStatusSerializer

@extend_schema(description="Return seat map with status (available|locked|sold)")
class SessionSeatMapAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, pk):
        session = get_object_or_404(Session, pk=pk)
        seats = session.room.seats.all().order_by("row", "number")

        sold_ids = set(session.tickets.values_list('seat_id', flat=True))

        locked_ids = set()
        try:
            client = cache.client.get_client()
            prefix = f"lock:session:{session.id}:seat:"
            keys = [f"{prefix}{s.id}" for s in seats]
            values = client.mget(keys)
            locked_ids = {s.id for s, v in zip(seats, values) if v}
        except Exception:
            for s in seats:
                if cache.get(f"lock:session:{session.id}:seat:{s.id}"):
                    locked_ids.add(s.id)

        serializer = SeatStatusSerializer(seats, many=True, context={'sold_ids': sold_ids, 'locked_ids': locked_ids})
        return Response({
            'session_id': session.id,
            'room': {'id': session.room.id, 'name': session.room.name},
            'seats': serializer.data
        })