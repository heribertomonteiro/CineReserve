from rest_framework import viewsets
from drf_spectacular.utils import extend_schema, extend_schema_view

from .models import Movie
from .serializers.movie_serializer import MovieSerializer


@extend_schema_view(
    list=extend_schema(
        tags=["Movies"],
        summary="Listar filmes",
        description="Retorna a lista paginada de filmes cadastrados.",
    ),
    retrieve=extend_schema(
        tags=["Movies"],
        summary="Detalhar filme",
        description="Retorna os detalhes de um filme pelo ID.",
    ),
)
class MovieViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Movie.objects.all().order_by("id")
    serializer_class = MovieSerializer
