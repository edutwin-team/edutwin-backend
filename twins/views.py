from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from .models import Twin, TwinSimulation
from .serializers import TwinSerializer, TwinSimulationSerializer
from .tasks import run_twin_simulation


class TwinViewSet(viewsets.ModelViewSet):
    queryset = Twin.objects.all()
    serializer_class = TwinSerializer
    permission_classes = [AllowAny]

    @action(detail=True, methods=["post"], url_path="simulate")
    def simulate(self, request, pk=None):
        twin = Twin.objects.get(pk=pk)
        content_type = request.data.get("content_type")  # "quiz" ou "course"
        content_id = request.data.get("content_id")

        if not content_type or not content_id:
            return Response(
                {"error": "content_type and content_id required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        run_twin_simulation.delay(twin.id, content_type, content_id)  # type: ignore

        return Response(
            {"message": "Simulation lancée"}, status=status.HTTP_202_ACCEPTED
        )


class TwinSimulationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = TwinSimulationSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        return TwinSimulation.objects.filter(twin_id=self.kwargs.get("twin_pk"))
