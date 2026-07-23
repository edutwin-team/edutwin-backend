"""Helpers partagés par tous les tests (pas découvert par le test runner)."""

from django.core.cache import cache
from rest_framework.test import APITestCase

from user.models import User, Role


def make_user(email="user@example.com", password="Test1234!", role=Role.teacher, **kw):
    kw.setdefault("first_name", "Test")
    kw.setdefault("last_name", "User")
    user = User.objects.create_user(email=email, password=password, role=role, **kw)
    user.is_active = True
    user.save()
    return user


def make_context(user, **kw):
    from twins.models import PedagogicalContext

    defaults = dict(
        name="Contexte", subject="Maths", level="L1", school="Hexagone",
        country="FR", academic_year="2025-2026",
    )
    defaults.update(kw)
    return PedagogicalContext.objects.create(user=user, **defaults)


def make_twin(user, context=None, **kw):
    from twins.models import DigitalTwin

    context = context or make_context(user)
    defaults = dict(name="Twin", age=20, average_grade=12.5)
    defaults.update(kw)
    return DigitalTwin.objects.create(user=user, context=context, **defaults)


def make_behavior(twin, **kw):
    from twins.models import Behavior

    defaults = dict(
        comprehension_level=70, motivation=60, learning_speed=50, error_rate=20,
        fatigue_level=30, attention_level=80, stress_level=10,
    )
    defaults.update(kw)
    return Behavior.objects.create(twin=twin, **defaults)


def make_quiz(user, with_questions=True, **kw):
    from content.models import Quiz, Question, Answer

    defaults = dict(title="Quiz", description="desc", passing_score=50, time_limit_minutes=15)
    defaults.update(kw)
    quiz = Quiz.objects.create(user=user, **defaults)
    if with_questions:
        q = Question.objects.create(quiz=quiz, text="2+2 ?")
        Answer.objects.create(question=q, text="4", is_correct=True)
        Answer.objects.create(question=q, text="5", is_correct=False)
    return quiz


def make_course(user, **kw):
    from content.models import Course

    defaults = dict(title="Cours", description="d", content="Contenu du cours")
    defaults.update(kw)
    return Course.objects.create(user=user, **defaults)


class BaseAPITest(APITestCase):
    """Vide le cache (compteurs de throttling DRF) avant chaque test."""

    def setUp(self):
        cache.clear()
        super().setUp()

    def auth(self, user=None, **kw):
        user = user or make_user(**kw)
        self.client.force_login(user)
        return user
