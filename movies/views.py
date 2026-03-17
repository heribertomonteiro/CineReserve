from rest_framework import viewsets

from .models import Movie
from .serializers.movie_serializer import MovieSerializer


class MovieViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Movie.objects.all().order_by("id")
    serializer_class = MovieSerializer
