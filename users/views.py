from rest_framework import generics
from drf_spectacular.utils import OpenApiResponse, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.contrib.auth.models import User
from .serializers.user_serializer import RegisterSerializer


@extend_schema(
    tags=["Auth"],
    summary="Registrar usuário",
    description="Cria uma nova conta de usuário para autenticação via JWT.",
)
class RegisterView(generics.CreateAPIView):

    queryset = User.objects.all()
    serializer_class = RegisterSerializer


@extend_schema(
    tags=["Auth"],
    summary="Login com JWT",
    description="Autentica usuário e retorna `access` e `refresh` tokens.",
    request=inline_serializer(
        name="TokenLoginRequest",
        fields={
            "username": serializers.CharField(),
            "password": serializers.CharField(),
        },
    ),
    responses={
        200: inline_serializer(
            name="TokenLoginResponse",
            fields={
                "refresh": serializers.CharField(),
                "access": serializers.CharField(),
            },
        ),
        401: OpenApiResponse(description="Credenciais inválidas."),
    },
)
class LoginView(TokenObtainPairView):
    pass


@extend_schema(
    tags=["Auth"],
    summary="Refresh do token JWT",
    description="Recebe um `refresh` token e retorna um novo `access` token.",
    request=inline_serializer(
        name="TokenRefreshRequest",
        fields={"refresh": serializers.CharField()},
    ),
    responses={
        200: inline_serializer(
            name="TokenRefreshResponse",
            fields={"access": serializers.CharField()},
        ),
        401: OpenApiResponse(description="Refresh token inválido ou expirado."),
    },
)
class RefreshView(TokenRefreshView):
    pass