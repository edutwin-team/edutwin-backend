from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers
from .views import TwinViewSet, TwinSimulationViewSet

router = DefaultRouter()
router.register("twins", TwinViewSet)

twin_router = routers.NestedDefaultRouter(router, "twins", lookup="twin")
twin_router.register("simulations", TwinSimulationViewSet, basename="twin-simulations")

urlpatterns = router.urls + twin_router.urls
