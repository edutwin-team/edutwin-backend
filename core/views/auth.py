from rest_framework import generics
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema

from core.serializers.auth import RegisterSerializer, UserSerializer


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    @extend_schema(tags=["Auth"], summary="Register a user")
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class MeView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer  # Helps drf-spectacular

    @extend_schema(
        tags=["Auth"],
        summary="Get current user",
        responses={200: UserSerializer},
    )
    def get(self, request):
        return Response(UserSerializer(request.user).data)
