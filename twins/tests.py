from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from rest_framework import status

from config.factories import (
    BaseAPITest,
    make_behavior,
    make_context,
    make_twin,
    make_user,
)
from .models import Behavior, DigitalTwin, LearningStyle, Objective, PedagogicalContext
from .serializers import DigitalTwinSerializer, PedagogicalContextSerializer


# ---------------------------------------------------------
# MODELS
# ---------------------------------------------------------
class TwinsModelTests(TestCase):
    def setUp(self):
        self.user = make_user(email="twin@example.com")

    def test_context_str(self):
        self.assertEqual(str(make_context(self.user, name="Algèbre")), "Algèbre")

    def test_objective_str_and_cascade(self):
        ctx = make_context(self.user)
        obj = Objective.objects.create(context=ctx, label="Comprendre les vecteurs")
        self.assertEqual(str(obj), "Comprendre les vecteurs")
        ctx.delete()
        self.assertFalse(Objective.objects.filter(pk=obj.pk).exists())

    def test_twin_str_and_related_names(self):
        twin = make_twin(self.user, name="Alice")
        self.assertEqual(str(twin), "Alice")
        self.assertIn(twin, self.user.twins.all())
        self.assertIn(twin, twin.context.twins.all())

    def test_behavior_str_and_defaults(self):
        twin = make_twin(self.user, name="Bob")
        behavior = make_behavior(twin)
        self.assertEqual(str(behavior), "Behavior of Bob")
        self.assertEqual(behavior.learning_style, LearningStyle.MIXED)
        self.assertEqual(behavior.curiosity_level, 50)
        self.assertEqual(twin.behavior, behavior)

    def test_twin_validators_reject_out_of_range(self):
        twin = make_twin(self.user, age=5, average_grade=25)
        with self.assertRaises(ValidationError):
            twin.full_clean()

    def test_behavior_validators_reject_out_of_range(self):
        behavior = make_behavior(make_twin(self.user), motivation=150)
        with self.assertRaises(ValidationError):
            behavior.full_clean()

    def test_deleting_user_cascades(self):
        make_behavior(make_twin(self.user))
        self.user.delete()
        self.assertEqual(DigitalTwin.objects.count(), 0)
        self.assertEqual(Behavior.objects.count(), 0)
        self.assertEqual(PedagogicalContext.objects.count(), 0)


# ---------------------------------------------------------
# SERIALIZERS
# ---------------------------------------------------------
class PedagogicalContextSerializerTests(TestCase):
    def setUp(self):
        self.user = make_user(email="ser@example.com")

    def _payload(self, **kw):
        data = dict(
            name="Contexte", subject="Maths", level="L1", school="Hexagone",
            country="FR", academic_year="2025-2026",
            objectives=[{"label": "Obj 1"}, {"label": "Obj 2"}],
        )
        data.update(kw)
        return data

    def test_create_nested_objectives(self):
        s = PedagogicalContextSerializer(data=self._payload())
        self.assertTrue(s.is_valid(), s.errors)
        self.assertEqual(s.save(user=self.user).objectives.count(), 2)

    def test_update_replaces_objectives(self):
        s = PedagogicalContextSerializer(data=self._payload())
        s.is_valid(raise_exception=True)
        ctx = s.save(user=self.user)

        s2 = PedagogicalContextSerializer(
            ctx, data=self._payload(objectives=[{"label": "Nouveau"}]), partial=True
        )
        self.assertTrue(s2.is_valid(), s2.errors)
        s2.save()
        self.assertEqual(ctx.objectives.count(), 1)
        self.assertEqual(ctx.objectives.first().label, "Nouveau")

    def test_update_without_objectives_keeps_them(self):
        s = PedagogicalContextSerializer(data=self._payload())
        s.is_valid(raise_exception=True)
        ctx = s.save(user=self.user)

        s2 = PedagogicalContextSerializer(ctx, data={"name": "Renommé"}, partial=True)
        self.assertTrue(s2.is_valid(), s2.errors)
        s2.save()
        ctx.refresh_from_db()
        self.assertEqual(ctx.name, "Renommé")
        self.assertEqual(ctx.objectives.count(), 2)

    def test_twins_field_counts_related_twins(self):
        ctx = make_context(self.user)
        make_twin(self.user, context=ctx)
        make_twin(self.user, context=ctx)
        self.assertEqual(PedagogicalContextSerializer(ctx).data["twins"], 2)


class DigitalTwinSerializerTests(TestCase):
    behavior_payload = dict(
        comprehension_level=80, motivation=70, learning_speed=60, error_rate=10,
        fatigue_level=20, attention_level=90, stress_level=5,
    )

    def setUp(self):
        self.user = make_user(email="dts@example.com")
        self.context = make_context(self.user)

    def _payload(self, **kw):
        data = dict(context=self.context.pk, name="Twin", age=20, average_grade=12.0)
        data.update(kw)
        return data

    def test_create_without_behavior(self):
        s = DigitalTwinSerializer(data=self._payload())
        self.assertTrue(s.is_valid(), s.errors)
        self.assertFalse(hasattr(s.save(user=self.user), "behavior"))

    def test_create_with_nested_behavior(self):
        s = DigitalTwinSerializer(data=self._payload(behavior=self.behavior_payload))
        self.assertTrue(s.is_valid(), s.errors)
        self.assertEqual(s.save(user=self.user).behavior.comprehension_level, 80)

    def test_update_or_creates_behavior(self):
        twin = make_twin(self.user, context=self.context)

        s = DigitalTwinSerializer(twin, data={"behavior": self.behavior_payload}, partial=True)
        self.assertTrue(s.is_valid(), s.errors)
        s.save()
        twin.refresh_from_db()
        self.assertEqual(twin.behavior.motivation, 70)

        s2 = DigitalTwinSerializer(
            twin, data={"behavior": {**self.behavior_payload, "motivation": 99}}, partial=True
        )
        self.assertTrue(s2.is_valid(), s2.errors)
        s2.save()
        twin.behavior.refresh_from_db()
        self.assertEqual(twin.behavior.motivation, 99)

    def test_context_name_is_exposed_readonly(self):
        twin = make_twin(self.user, context=self.context)
        self.assertEqual(DigitalTwinSerializer(twin).data["context_name"], self.context.name)


# ---------------------------------------------------------
# VIEWSETS
# ---------------------------------------------------------
class PedagogicalContextViewSetTests(BaseAPITest):
    def setUp(self):
        super().setUp()
        self.user = make_user(email="ctxapi@example.com")
        self.other = make_user(email="other@example.com")
        self.url = reverse("context-list")

    def test_requires_authentication(self):
        self.assertEqual(self.client.get(self.url).status_code, status.HTTP_403_FORBIDDEN)

    def test_create_assigns_current_user(self):
        self.client.force_login(self.user)
        payload = dict(
            name="C", subject="S", level="L", school="E", country="FR",
            academic_year="2025", objectives=[{"label": "O"}],
        )
        res = self.client.post(self.url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(PedagogicalContext.objects.get().user, self.user)

    def test_list_is_scoped_to_current_user(self):
        make_context(self.user, name="Mien")
        make_context(self.other, name="Autre")
        self.client.force_login(self.user)

        res = self.client.get(self.url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual([c["name"] for c in res.data], ["Mien"])

    def test_cannot_retrieve_other_users_context(self):
        ctx = make_context(self.other)
        self.client.force_login(self.user)
        res = self.client.get(reverse("context-detail", args=[ctx.pk]))
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete(self):
        ctx = make_context(self.user)
        self.client.force_login(self.user)
        res = self.client.delete(reverse("context-detail", args=[ctx.pk]))
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(PedagogicalContext.objects.count(), 0)


class DigitalTwinViewSetTests(BaseAPITest):
    def setUp(self):
        super().setUp()
        self.user = make_user(email="twinapi@example.com")
        self.other = make_user(email="twinother@example.com")
        self.context = make_context(self.user)
        self.url = reverse("learner-list")

    def test_create_assigns_current_user(self):
        self.client.force_login(self.user)
        res = self.client.post(
            self.url,
            {"context": self.context.pk, "name": "Zoe", "age": 18, "average_grade": 14.0},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(DigitalTwin.objects.get().user, self.user)

    def test_list_scoped_to_user(self):
        make_twin(self.user, context=self.context, name="Mien")
        make_twin(self.other, name="Autre")
        self.client.force_login(self.user)
        self.assertEqual([t["name"] for t in self.client.get(self.url).data], ["Mien"])

    def test_patch_twin(self):
        twin = make_twin(self.user, context=self.context)
        self.client.force_login(self.user)
        res = self.client.patch(
            reverse("learner-detail", args=[twin.pk]), {"name": "Renommé"}, format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        twin.refresh_from_db()
        self.assertEqual(twin.name, "Renommé")

    def test_other_user_twin_is_404(self):
        twin = make_twin(self.other)
        self.client.force_login(self.user)
        res = self.client.get(reverse("learner-detail", args=[twin.pk]))
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)


class ObjectiveAndBehaviorViewSetTests(BaseAPITest):
    """⚠️ Ces deux viewsets ne filtrent PAS par utilisateur (queryset = .all())."""

    def setUp(self):
        super().setUp()
        self.user = make_user(email="ob@example.com")
        self.context = make_context(self.user)
        self.objective = Objective.objects.create(context=self.context, label="Obj")
        self.twin = make_twin(self.user, context=self.context)
        self.behavior = make_behavior(self.twin)
        self.client.force_login(self.user)

    def test_objective_list_and_detail(self):
        res = self.client.get(reverse("objective-list"))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(
            self.client.get(reverse("objective-detail", args=[self.objective.pk])).data["label"],
            "Obj",
        )

    def test_objective_patch(self):
        res = self.client.patch(
            reverse("objective-detail", args=[self.objective.pk]),
            {"label": "Modifié"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.objective.refresh_from_db()
        self.assertEqual(self.objective.label, "Modifié")

    def test_behavior_list_and_patch(self):
        self.assertEqual(len(self.client.get(reverse("behavior-list")).data), 1)

        res = self.client.patch(
            reverse("behavior-detail", args=[self.behavior.pk]),
            {"motivation": 42},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.behavior.refresh_from_db()
        self.assertEqual(self.behavior.motivation, 42)
