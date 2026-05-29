from rest_framework.routers import DefaultRouter
from .views import PedagogicalContextViewSet, ObjectiveViewSet

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

urlpatterns = router.urls