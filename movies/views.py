from django.shortcuts import render

# Create your views here.
from rest_framework import viewsets
from .models import Movie
from .serializers.movie_serializer import MovieSerializer


class MovieViewSet(viewsets.ModelViewSet):

    queryset = Movie.objects.all()

    serializer_class = MovieSerializer