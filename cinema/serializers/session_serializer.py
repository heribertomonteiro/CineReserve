from rest_framework import serializers
from ..models import Session


class SessionListSerializer(serializers.ModelSerializer):
    room = serializers.StringRelatedField()
    movie_title = serializers.CharField(source="movie.title", read_only=True)
    movie_duration = serializers.IntegerField(source="movie.duration", read_only=True)

    class Meta:
        model = Session
        fields = ("id", "movie_title", "movie_duration", "room", "starts_at", "price")


class SessionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Session
        fields = ("id", "movie", "room", "starts_at", "price")
        read_only_fields = ("id",)