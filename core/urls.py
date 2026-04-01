from django.contrib import admin
from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from edutwin_backend.core.views.auth import RegisterView, MeView
from edutwin_backend.core.views.quiz import StartQuizAttemptView, SubmitQuizAttemptView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/register/", RegisterView.as_view(), name="auth-register"),
    path("api/auth/token/", TokenObtainPairView.as_view(), name="token-obtain-pair"),
    path("api/auth/token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("api/auth/me/", MeView.as_view(), name="auth-me"),
    path(
        "api/quizzes/<int:quiz_id>/attempts/",
        StartQuizAttemptView.as_view(),
        name="quiz-start-attempt",
    ),
    path(
        "api/attempts/<int:attempt_id>/submit/",
        SubmitQuizAttemptView.as_view(),
        name="quiz-submit-attempt",
    ),
]
