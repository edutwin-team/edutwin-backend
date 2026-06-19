from rest_framework.routers import DefaultRouter
from .views import PedagogicalContextViewSet, ObjectiveViewSet,DigitalTwinViewSet,BehaviorViewSet

router = DefaultRouter()

router.register(
    r"contexts",
    PedagogicalContextViewSet,
    basename="context"
)

router.register(
    r"objectives",
    ObjectiveViewSet,
    basename="objective"
)
router.register(r"learners", DigitalTwinViewSet, basename="learner")
router.register(r"behaviors", BehaviorViewSet, basename="behavior")

urlpatterns = router.urls