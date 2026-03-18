from rest_framework import serializers, status
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.shortcuts import get_object_or_404
from django.core.cache import cache
from django.db import transaction, IntegrityError
from drf_spectacular.utils import ( OpenApiExample, OpenApiParameter, OpenApiResponse, extend_schema, extend_schema_view, inline_serializer,)
from .models import Session, Seat, Ticket
from .cache_utils import ( MOVIE_SESSIONS_CACHE_TTL, invalidate_movie_sessions_cache, invalidate_session_seat_map_cache, movie_sessions_cache_key, SEAT_MAP_CACHE_TTL, session_seat_map_cache_key,)
from .serializers.session_serializer import SessionListSerializer
from .serializers.seat_serializer import SeatStatusSerializer
from .serializers.ticket_serializer import TicketCreateSerializer, MyTicketSerializer
from django.utils import timezone

from cinema.tasks import send_ticket_confirmation_email


SeatMapResponseSerializer = inline_serializer(
    name="SeatMapResponse",
    fields={
        "session_id": serializers.IntegerField(),
        "room": inline_serializer(
            name="SeatMapRoom",
            fields={
                "id": serializers.IntegerField(),
                "name": serializers.CharField(),
            },
        ),
        "seats": SeatStatusSerializer(many=True),
    },
)

SeatLockResponseSerializer = inline_serializer(
    name="SeatLockResponse",
    fields={
        "status": serializers.CharField(),
        "seat_id": serializers.IntegerField(),
    },
)

TicketCreateResponseSerializer = inline_serializer(
    name="TicketCreateResponse",
    fields={
        "status": serializers.CharField(),
        "ticket_id": serializers.IntegerField(),
    },
)

ErrorDetailSerializer = inline_serializer(
    name="ErrorDetail",
    fields={"detail": serializers.CharField()},
)

@extend_schema_view(
    get=extend_schema(
        tags=["Cinema"],
        summary="Listar sessões",
        description="Retorna a lista paginada de todas as sessões cadastradas.",
        responses=SessionListSerializer(many=True),
    )
)
class SessionListCreateAPIView(ListAPIView):
    queryset = Session.objects.select_related("movie", "room").order_by("starts_at")
    permission_classes = [AllowAny]
    serializer_class = SessionListSerializer


@extend_schema_view(
    get=extend_schema(
        tags=["Cinema"],
        summary="Listar sessões por filme",
        description="Retorna sessões de um filme específico, ordenadas por data/hora.",
        parameters=[
            OpenApiParameter(
                name="movie_id",
                location=OpenApiParameter.PATH,
                required=True,
                type=int,
                description="ID do filme.",
            )
        ],
        responses=SessionListSerializer(many=True),
    )
)
class MovieSessionsAPIView(ListAPIView):
    serializer_class = SessionListSerializer

    def list(self, request, *args, **kwargs):
        movie_id = kwargs["movie_id"]

        cache_key = movie_sessions_cache_key(movie_id, request.get_full_path())

        cached = cache.get(cache_key)
        if cached:
            return Response(cached)

        response = super().list(request, *args, **kwargs)

        cache.set(cache_key, response.data, timeout=MOVIE_SESSIONS_CACHE_TTL)

        return response

    def get_queryset(self):
        movie_id = self.kwargs["movie_id"]

        return (
            Session.objects
            .filter(movie_id=movie_id)
            .select_related("room")
            .order_by("starts_at")
        )


@extend_schema_view(
    get=extend_schema(
        tags=["Cinema"],
        summary="Mapa de assentos da sessão",
        description="Retorna o mapa de assentos com status `available`, `reserved` ou `purchased`.",
        parameters=[
            OpenApiParameter(
                name="pk",
                location=OpenApiParameter.PATH,
                required=True,
                type=int,
                description="ID da sessão.",
            )
        ],
        responses={
            200: OpenApiResponse(response=SeatMapResponseSerializer),
            404: OpenApiResponse(response=ErrorDetailSerializer),
        },
    )
)
class SessionSeatMapAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, pk):
        cache_key = session_seat_map_cache_key(pk, request.get_full_path())
        cached = cache.get(cache_key)
        if cached:
            return Response(cached)

        session = get_object_or_404(Session, pk=pk)
        seats = (
            session.room.seats
            .only("id", "row", "number", "room_id")
            .order_by("row", "number")
        )

        purchased_ids = set(session.tickets.values_list('seat_id', flat=True))

        reserved_ids = set()
        try:
            keys = [f"lock:session:{session.id}:seat:{s.id}" for s in seats]
            found = cache.get_many(keys)
            reserved_ids = {s.id for s, k in zip(seats, keys) if k in found}
        except Exception:
            for s in seats:
                if cache.get(f"lock:session:{session.id}:seat:{s.id}"):
                    reserved_ids.add(s.id)

        serializer = SeatStatusSerializer(
            seats,
            many=True,
            context={'purchased_ids': purchased_ids, 'reserved_ids': reserved_ids},
        )
        payload = {
            'session_id': session.id,
            'room': {'id': session.room.id, 'name': session.room.name},
            'seats': serializer.data
        }
        cache.set(cache_key, payload, timeout=SEAT_MAP_CACHE_TTL)
        return Response(payload)


@extend_schema_view(
    post=extend_schema(
        tags=["Cinema"],
        summary="Reservar assento (lock)",
        description="Cria um lock temporário de 10 minutos para o assento na sessão.",
        request=None,
        parameters=[
            OpenApiParameter(
                name="session_pk",
                location=OpenApiParameter.PATH,
                required=True,
                type=int,
                description="ID da sessão.",
            ),
            OpenApiParameter(
                name="seat_id",
                location=OpenApiParameter.PATH,
                required=True,
                type=int,
                description="ID do assento.",
            ),
        ],
        responses={
            201: OpenApiResponse(
                response=SeatLockResponseSerializer,
                examples=[
                    OpenApiExample(
                        "Reserva criada",
                        value={"status": "reserved", "seat_id": 12},
                        status_codes=["201"],
                    )
                ],
            ),
            400: OpenApiResponse(response=ErrorDetailSerializer),
            401: OpenApiResponse(description="Não autenticado."),
            409: OpenApiResponse(response=ErrorDetailSerializer),
        },
    ),
    delete=extend_schema(
        tags=["Cinema"],
        summary="Liberar assento (unlock)",
        description="Remove o lock do assento, desde que o usuário autenticado seja o dono da reserva.",
        request=None,
        parameters=[
            OpenApiParameter(
                name="session_pk",
                location=OpenApiParameter.PATH,
                required=True,
                type=int,
                description="ID da sessão.",
            ),
            OpenApiParameter(
                name="seat_id",
                location=OpenApiParameter.PATH,
                required=True,
                type=int,
                description="ID do assento.",
            ),
        ],
        responses={
            204: OpenApiResponse(description="Lock removido com sucesso."),
            401: OpenApiResponse(description="Não autenticado."),
            403: OpenApiResponse(response=ErrorDetailSerializer),
            404: OpenApiResponse(response=ErrorDetailSerializer),
        },
    ),
)
class SeatLockAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, session_pk, seat_id):
        session = get_object_or_404(Session, pk=session_pk)
        seat = get_object_or_404(Seat, pk=seat_id, room=session.room)

        key = f"lock:session:{session.id}:seat:{seat.id}"
        owner = str(request.user.id)

        acquired = cache.add(key, owner, timeout=600)

        if not acquired:
            return Response(
                {"detail": "Seat already reserved"},
                status=status.HTTP_409_CONFLICT
            )

        if session.tickets.filter(seat_id=seat.id).exists():
            cache.delete(key)
            invalidate_session_seat_map_cache(session.id)
            return Response(
                {"detail": "Seat already purchased"},
                status=status.HTTP_400_BAD_REQUEST
            )

        invalidate_session_seat_map_cache(session.id)

        return Response(
            {"status": "reserved", "seat_id": seat.id},
            status=status.HTTP_201_CREATED
        )

    def delete(self, request, session_pk, seat_id):
        session = get_object_or_404(Session, pk=session_pk)
        seat = get_object_or_404(Seat, pk=seat_id, room=session.room)

        key = f"lock:session:{session.id}:seat:{seat.id}"
        owner = cache.get(key)

        if owner is None:
            return Response(
                {"detail": "Seat not reserved"},
                status=status.HTTP_404_NOT_FOUND
            )

        if str(request.user.id) != str(owner):
            return Response(
                {"detail": "Not owner of reservation"},
                status=status.HTTP_403_FORBIDDEN
            )

        cache.delete(key)
        invalidate_session_seat_map_cache(session.id)
        return Response(status=status.HTTP_204_NO_CONTENT)

class TicketCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Cinema"],
        summary="Finalizar compra (checkout)",
        description=(
            "Cria um ticket para um assento previamente reservado pelo próprio usuário "
            "e dispara envio de e-mail de confirmação em background via Celery."
        ),
        request=TicketCreateSerializer,
        responses={
            201: OpenApiResponse(
                response=TicketCreateResponseSerializer,
                examples=[
                    OpenApiExample(
                        "Compra concluída",
                        value={"status": "success", "ticket_id": 42},
                        status_codes=["201"],
                    )
                ],
            ),
            400: OpenApiResponse(response=ErrorDetailSerializer),
            401: OpenApiResponse(description="Não autenticado."),
            403: OpenApiResponse(response=ErrorDetailSerializer),
            409: OpenApiResponse(response=ErrorDetailSerializer),
        },
    )
    def post(self, request):
        serializer = TicketCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        session_id = serializer.validated_data["session_id"]
        seat_id = serializer.validated_data["seat_id"]

        session = get_object_or_404(Session, pk=session_id)
        seat = get_object_or_404(Seat, pk=seat_id, room=session.room)

        lock_key = f"lock:session:{session.id}:seat:{seat.id}"
        owner = cache.get(lock_key)

        if owner is None:
            return Response(
                {"detail": "Seat not reserved"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if str(owner) != str(request.user.id):
            return Response(
                {"detail": "You do not own this reservation"},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            with transaction.atomic():

                ticket = Ticket.objects.create(
                    user=request.user,
                    session=session,
                    seat=seat
                )

                cache.delete(lock_key)
                invalidate_session_seat_map_cache(session.id)

                transaction.on_commit(lambda: send_ticket_confirmation_email.delay(ticket.id))

                return Response(
                    {"status": "success", "ticket_id": ticket.id},
                    status=status.HTTP_201_CREATED
                )

        except IntegrityError:
            return Response(
                {"detail": "Seat already purchased"},
                status=status.HTTP_409_CONFLICT
            )


@extend_schema_view(
    get=extend_schema(
        tags=["Cinema"],
        summary="Listar meus ingressos",
        description="Retorna ingressos do usuário autenticado com filtro opcional por escopo.",
        parameters=[
            OpenApiParameter(
                name="scope",
                location=OpenApiParameter.QUERY,
                required=False,
                type=str,
                enum=["all", "active", "history"],
                description="Filtro de período dos ingressos. Padrão: `all`.",
            )
        ],
        responses={
            200: MyTicketSerializer(many=True),
            401: OpenApiResponse(description="Não autenticado."),
        },
    )
)
class MyTicketsAPIView(ListAPIView):
    serializer_class = MyTicketSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        scope = self.request.query_params.get("scope", "all")

        queryset = (
            Ticket.objects
            .filter(user=user)
            .select_related("session", "session__movie", "session__room", "seat")
        )

        now = timezone.now()

        if scope == "history":
            queryset = queryset.filter(session__starts_at__lt=now)
        elif scope == "active":
            queryset = queryset.filter(session__starts_at__gte=now)

        return queryset.order_by("session__starts_at")