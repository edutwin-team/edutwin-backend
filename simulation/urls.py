from django.urls import path
from .views import SimulateQuizView, SimulateCourseView, SimulationHistoryView

urlpatterns = [
    path("quiz/", SimulateQuizView.as_view(), name="simulate-quiz"),
    path("course/", SimulateCourseView.as_view(), name="simulate-course"),
    path("history/", SimulationHistoryView.as_view(), name="simulation-history"),
]
