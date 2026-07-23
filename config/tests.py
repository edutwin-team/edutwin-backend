from django.conf import settings
from django.test import TestCase
from django.urls import reverse
from rest_framework import status

from config.factories import BaseAPITest, make_user


class ProjectRoutesTests(BaseAPITest):
    def test_csrf_endpoint_returns_token(self):
        res = self.client.get("/api/csrf/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(res.json()["csrfToken"])

    def test_openapi_schema_is_generated(self):
        res = self.client.get(reverse("schema"))
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_swagger_ui_renders(self):
        self.assertEqual(self.client.get(reverse("swagger-ui")).status_code, 200)

    def test_redoc_renders(self):
        self.assertEqual(self.client.get(reverse("redoc")).status_code, 200)

    def test_admin_redirects_anonymous_user(self):
        self.assertEqual(self.client.get("/admin/").status_code, 302)

    def test_admin_accessible_for_superuser(self):
        from user.models import User

        User.objects.create_superuser(email="root@example.com", password="Root1234!")
        self.client.login(email="root@example.com", password="Root1234!")
        self.assertEqual(self.client.get("/admin/").status_code, 200)

    def test_unknown_route_is_404(self):
        self.assertEqual(self.client.get("/api/nope/").status_code, 404)


class SettingsTests(TestCase):
    def test_custom_user_model(self):
        self.assertEqual(settings.AUTH_USER_MODEL, "user.User")

    def test_default_permission_is_authenticated(self):
        self.assertIn(
            "rest_framework.permissions.IsAuthenticated",
            settings.REST_FRAMEWORK["DEFAULT_PERMISSION_CLASSES"],
        )

    def test_ci_uses_sqlite(self):
        self.assertIn("sqlite3", settings.DATABASES["default"]["ENGINE"])


class AdminRegistrationTests(TestCase):
    def test_user_is_registered_in_admin(self):
        from django.contrib import admin

        from user.models import User

        self.assertIn(User, admin.site._registry)
