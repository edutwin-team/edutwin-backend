"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

# config/urls.py
from django.contrib import admin
from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

from core.views.auth import RegisterView, MeView
from core.views.quiz import StartQuizView, SubmitQuizView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    path("api/auth/register/", RegisterView.as_view(), name="auth-register"),
    path("api/auth/token/", TokenObtainPairView.as_view(), name="token-obtain-pair"),
    path("api/auth/token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("api/auth/me/", MeView.as_view(), name="auth-me"),
    path(
        "api/quizzes/<int:quiz_id>/attempts/",
        StartQuizView.as_view(),
        name="quiz-start-attempt",
    ),
    path(
        "api/attempts/<int:attempt_id>/submit/",
        SubmitQuizView.as_view(),
        name="quiz-submit-attempt",
    ),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    # 2. Serves the interactive Swagger UI
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    # 3. Optional: Serves Redoc (an alternative, cleaner UI)
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]
