from unittest.mock import patch

from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework import status
from rest_framework.test import APIRequestFactory

from config.factories import BaseAPITest, make_user
from .models import EducationalProfile, Role, User
from .permissions import IsAdminOrTeacherOrReadOnly, IsOwnerOrAdmin
from .serializers import UserSerializer
from .tokens import account_activation_token
from .utils import send_verification_email


# ---------------------------------------------------------
# MODELS / MANAGER
# ---------------------------------------------------------
class UserManagerTests(TestCase):
    def test_create_user_requires_email(self):
        with self.assertRaises(ValueError):
            User.objects.create_user(email="", password="x")

    def test_create_user_defaults_inactive_and_teacher(self):
        user = User.objects.create_user(email="A@Example.COM", password="pwd")
        self.assertFalse(user.is_active)
        self.assertEqual(user.role, Role.teacher)
        self.assertTrue(user.check_password("pwd"))
        # normalize_email ne touche que le domaine
        self.assertEqual(user.email, "A@example.com")

    def test_create_superuser(self):
        su = User.objects.create_superuser(email="admin@example.com", password="pwd")
        self.assertTrue(su.is_staff)
        self.assertTrue(su.is_superuser)
        self.assertTrue(su.is_active)
        self.assertEqual(su.role, Role.admin)

    def test_username_field_is_email(self):
        self.assertEqual(User.USERNAME_FIELD, "email")
        self.assertEqual(User.REQUIRED_FIELDS, [])


class EducationalProfileTests(TestCase):
    def test_str_returns_email(self):
        user = make_user(email="edu@example.com")
        profile = EducationalProfile.objects.create(user=user, school="Hexagone")
        self.assertEqual(str(profile), "edu@example.com")
        self.assertEqual(user.educational_profile, profile)


# ---------------------------------------------------------
# SERIALIZER
# ---------------------------------------------------------
class UserSerializerTests(TestCase):
    payload = {
        "email": "s@example.com",
        "password": "Test1234!",
        "first_name": "Jean",
        "last_name": "Dupont",
    }

    def test_create_hashes_password_and_keeps_inactive(self):
        s = UserSerializer(data=self.payload)
        self.assertTrue(s.is_valid(), s.errors)
        user = s.save()
        self.assertFalse(user.is_active)
        self.assertNotEqual(user.password, "Test1234!")
        self.assertTrue(user.check_password("Test1234!"))

    def test_create_with_nested_educational_profile(self):
        data = {**self.payload, "educational_profile": {"school": "Hexagone", "experience_years": 3}}
        s = UserSerializer(data=data)
        self.assertTrue(s.is_valid(), s.errors)
        user = s.save()
        self.assertEqual(user.educational_profile.school, "Hexagone")
        self.assertEqual(user.educational_profile.experience_years, 3)

    def test_get_role_returns_name(self):
        user = make_user(email="r@example.com", role=Role.admin)
        self.assertEqual(UserSerializer(user).data["role"], "admin")

    def test_password_is_write_only(self):
        user = make_user(email="w@example.com")
        self.assertNotIn("password", UserSerializer(user).data)

    def test_update_creates_profile_if_missing(self):
        user = make_user(email="u1@example.com")
        s = UserSerializer(user, data={"educational_profile": {"school": "X"}}, partial=True)
        self.assertTrue(s.is_valid(), s.errors)
        s.save()
        self.assertEqual(user.educational_profile.school, "X")

    def test_update_existing_profile(self):
        user = make_user(email="u2@example.com")
        EducationalProfile.objects.create(user=user, school="Old")
        s = UserSerializer(user, data={"educational_profile": {"school": "New"}}, partial=True)
        self.assertTrue(s.is_valid(), s.errors)
        s.save()
        user.educational_profile.refresh_from_db()
        self.assertEqual(user.educational_profile.school, "New")

    def test_update_simple_field(self):
        user = make_user(email="u3@example.com")
        s = UserSerializer(user, data={"first_name": "Zoe"}, partial=True)
        self.assertTrue(s.is_valid(), s.errors)
        s.save()
        user.refresh_from_db()
        self.assertEqual(user.first_name, "Zoe")

    def test_duplicate_email_rejected(self):
        make_user(email="dup@example.com")
        s = UserSerializer(data={**self.payload, "email": "dup@example.com"})
        self.assertFalse(s.is_valid())
        self.assertIn("email", s.errors)


# ---------------------------------------------------------
# PERMISSIONS
# ---------------------------------------------------------
class PermissionTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.student = make_user(email="stu@example.com", role=Role.student)
        self.teacher = make_user(email="tea@example.com", role=Role.teacher)
        self.admin = make_user(email="adm@example.com", role=Role.admin)

    def _req(self, method, user):
        request = getattr(self.factory, method)("/")
        request.user = user
        return request

    def test_read_allowed_for_any_authenticated(self):
        perm = IsAdminOrTeacherOrReadOnly()
        self.assertTrue(perm.has_permission(self._req("get", self.student), None))

    def test_read_denied_for_anonymous(self):
        from django.contrib.auth.models import AnonymousUser

        perm = IsAdminOrTeacherOrReadOnly()
        self.assertFalse(perm.has_permission(self._req("get", AnonymousUser()), None))

    def test_write_denied_for_student(self):
        perm = IsAdminOrTeacherOrReadOnly()
        self.assertFalse(perm.has_permission(self._req("post", self.student), None))

    def test_write_allowed_for_teacher_and_admin(self):
        perm = IsAdminOrTeacherOrReadOnly()
        self.assertTrue(perm.has_permission(self._req("post", self.teacher), None))
        self.assertTrue(perm.has_permission(self._req("post", self.admin), None))

    def test_object_permission_safe_method(self):
        perm = IsOwnerOrAdmin()
        obj = type("Obj", (), {"created_by": self.teacher})()
        self.assertTrue(perm.has_object_permission(self._req("get", self.student), None, obj))

    def test_object_permission_admin_bypasses_ownership(self):
        perm = IsOwnerOrAdmin()
        obj = type("Obj", (), {"created_by": self.teacher})()
        self.assertTrue(perm.has_object_permission(self._req("put", self.admin), None, obj))

    def test_object_permission_owner_only(self):
        perm = IsOwnerOrAdmin()
        obj = type("Obj", (), {"created_by": self.teacher})()
        self.assertTrue(perm.has_object_permission(self._req("put", self.teacher), None, obj))
        self.assertFalse(perm.has_object_permission(self._req("put", self.student), None, obj))


# ---------------------------------------------------------
# UTILS
# ---------------------------------------------------------
@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    DEFAULT_FROM_EMAIL="noreply@edutwin.test",
)
class SendVerificationEmailTests(TestCase):
    def test_email_contains_activation_link(self):
        user = make_user(email="verify@example.com")
        request = APIRequestFactory().get("/")
        send_verification_email(user, request)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["verify@example.com"])
        self.assertIn("/api/auth/activate/", mail.outbox[0].body)


# ---------------------------------------------------------
# AUTH ENDPOINTS
# ---------------------------------------------------------
class RegisterViewTests(BaseAPITest):
    url_name = "register"

    def test_register_success(self):
        payload = {
            "email": "new@example.com",
            "password": "Test1234!",
            "first_name": "New",
            "last_name": "User",
        }
        res = self.client.post(reverse(self.url_name), payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(email="new@example.com").exists())

    def test_register_invalid_email(self):
        res = self.client.post(
            reverse(self.url_name),
            {"email": "not-an-email", "password": "x", "first_name": "a", "last_name": "b"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", res.data)

    def test_register_missing_password(self):
        res = self.client.post(
            reverse(self.url_name),
            {"email": "x@example.com", "first_name": "a", "last_name": "b"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)


class LoginLogoutTests(BaseAPITest):
    def setUp(self):
        super().setUp()
        self.user = make_user(email="login@example.com", password="Test1234!")

    def test_login_success(self):
        res = self.client.post(
            reverse("login"),
            {"email": "login@example.com", "password": "Test1234!"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("_auth_user_id", self.client.session)

    def test_login_wrong_password(self):
        res = self.client.post(
            reverse("login"),
            {"email": "login@example.com", "password": "wrong"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_unknown_email(self):
        res = self.client.post(
            reverse("login"), {"email": "ghost@example.com", "password": "x"}, format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_requires_auth(self):
        self.assertEqual(
            self.client.post(reverse("logout")).status_code, status.HTTP_403_FORBIDDEN
        )

    def test_logout_success(self):
        self.client.force_login(self.user)
        res = self.client.post(reverse("logout"))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertNotIn("_auth_user_id", self.client.session)


class ActivateViewTests(BaseAPITest):
    def _url(self, user, token):
        return reverse(
            "activate",
            kwargs={"uidb64": urlsafe_base64_encode(force_bytes(user.pk)), "token": token},
        )

    def test_activate_valid_token(self):
        user = User.objects.create_user(email="act@example.com", password="pwd")
        self.assertFalse(user.is_active)
        token = account_activation_token.make_token(user)

        res = self.client.get(self._url(user, token))
        user.refresh_from_db()

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(user.is_active)
        self.assertTrue(res.context["success"])

    def test_activate_invalid_token(self):
        user = User.objects.create_user(email="act2@example.com", password="pwd")
        res = self.client.get(self._url(user, "bad-token"))
        user.refresh_from_db()
        self.assertFalse(user.is_active)
        self.assertFalse(res.context["success"])

    def test_activate_unknown_uid(self):
        res = self.client.get(
            reverse("activate", kwargs={"uidb64": urlsafe_base64_encode(b"99999"), "token": "t"})
        )
        self.assertFalse(res.context["success"])

    def test_activate_malformed_uid(self):
        res = self.client.get(reverse("activate", kwargs={"uidb64": "@@@", "token": "t"}))
        self.assertFalse(res.context["success"])


class MeViewTests(BaseAPITest):
    def setUp(self):
        super().setUp()
        self.user = make_user(email="me@example.com")
        self.url = reverse("me")

    def test_requires_authentication(self):
        self.assertEqual(self.client.get(self.url).status_code, status.HTTP_403_FORBIDDEN)

    def test_get_returns_current_user(self):
        self.client.force_login(self.user)
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["email"], "me@example.com")
        self.assertEqual(res.data["role"], "teacher")

    def test_put_updates_fields(self):
        self.client.force_login(self.user)
        res = self.client.put(self.url, {"birthdate": "2000-01-01"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(str(self.user.birthdate), "2000-01-01")

    def test_put_ignores_email_change(self):
        self.client.force_login(self.user)
        self.client.put(self.url, {"email": "hacker@example.com"}, format="json")
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "me@example.com")

    def test_put_invalid_payload(self):
        self.client.force_login(self.user)
        res = self.client.put(self.url, {"birthdate": "pas-une-date"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)


class ChangePasswordTests(BaseAPITest):
    def setUp(self):
        super().setUp()
        self.user = make_user(email="pwd@example.com", password="Old1234!")
        self.url = reverse("change_password")
        self.client.force_login(self.user)

    def test_missing_fields(self):
        res = self.client.put(self.url, {"old_password": "Old1234!"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_wrong_old_password(self):
        res = self.client.put(
            self.url, {"old_password": "nope", "new_password": "New1234!"}, format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_success_keeps_session(self):
        res = self.client.put(
            self.url, {"old_password": "Old1234!", "new_password": "New1234!"}, format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("New1234!"))
        self.assertIn("_auth_user_id", self.client.session)


class DeleteUserTests(BaseAPITest):
    def test_requires_authentication(self):
        self.assertEqual(
            self.client.delete(reverse("delete-user")).status_code, status.HTTP_403_FORBIDDEN
        )

    def test_delete_removes_user_and_session(self):
        user = make_user(email="del@example.com")
        self.client.force_login(user)
        res = self.client.delete(reverse("delete-user"))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertFalse(User.objects.filter(pk=user.pk).exists())
        self.assertNotIn("_auth_user_id", self.client.session)
