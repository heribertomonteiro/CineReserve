from django.shortcuts import render

# Create your views here.

from rest_framework import generics
from django.contrib.auth.models import User
from .serializers.user_serializer import RegisterSerializer


class RegisterView(generics.CreateAPIView):

    queryset = User.objects.all()
    serializer_class = RegisterSerializer