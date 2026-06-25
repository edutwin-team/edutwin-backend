from rest_framework import viewsets
from .models import PedagogicalContext, Objective,DigitalTwin, Behavior
from .serializers import PedagogicalContextSerializer, ObjectiveSerializer,DigitalTwinSerializer, BehaviorSerializer


class PedagogicalContextViewSet(viewsets.ModelViewSet):
    serializer_class = PedagogicalContextSerializer

    def get_queryset(self):
        # each user see hes own contexts
        return PedagogicalContext.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class ObjectiveViewSet(viewsets.ModelViewSet):
    queryset = Objective.objects.all()
    serializer_class = ObjectiveSerializer
    
class DigitalTwinViewSet(viewsets.ModelViewSet):
    serializer_class = DigitalTwinSerializer

    def get_queryset(self):
        return DigitalTwin.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
        
class BehaviorViewSet(viewsets.ModelViewSet):
    queryset = Behavior.objects.all()
    serializer_class = BehaviorSerializer