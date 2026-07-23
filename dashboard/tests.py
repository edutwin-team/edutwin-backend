from datetime import timedelta

from django.urls import reverse
from django.utils import timezone
from rest_framework import status

from config.factories import (
    BaseAPITest,
    make_context,
    make_course,
    make_quiz,
    make_twin,
    make_user,
)
from simulation.models import SimulationResult


class DashboardViewTests(BaseAPITest):
    def setUp(self):
        super().setUp()
        self.user = make_user(email="dash@example.com")
        self.other = make_user(email="dashother@example.com")
        self.url = reverse("dashboard")

    def _simulation(self, user, twin, days_ago=0):
        result = SimulationResult.objects.create(
            user=user, twin=twin, simulation_type="quiz",
            simulated_score=50.0, simulated_time_seconds=60,
        )
        if days_ago:
            SimulationResult.objects.filter(pk=result.pk).update(
                created_at=timezone.now() - timedelta(days=days_ago)
            )
        return result

    def test_requires_authentication(self):
        self.assertEqual(self.client.get(self.url).status_code, status.HTTP_403_FORBIDDEN)

    def test_empty_dashboard(self):
        self.client.force_login(self.user)
        res = self.client.get(self.url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(
            res.data["counts"],
            {"contexts": 0, "twins": 0, "quizzes": 0, "simulations": 0},
        )
        self.assertEqual(res.data["last_7_days_total"], 0)
        self.assertEqual(len(res.data["weekly_simulations"]), 7)
        self.assertEqual(res.data["last_twins"], [])

    def test_counts_are_scoped_to_user(self):
        context = make_context(self.user)
        twin = make_twin(self.user, context=context)
        make_quiz(self.user, with_questions=False)
        make_course(self.user)
        self._simulation(self.user, twin)

        # Données d'un autre utilisateur : ne doivent pas être comptées
        other_twin = make_twin(self.other)
        make_quiz(self.other, with_questions=False)
        self._simulation(self.other, other_twin)

        self.client.force_login(self.user)
        counts = self.client.get(self.url).data["counts"]

        self.assertEqual(counts["contexts"], 1)
        self.assertEqual(counts["twins"], 1)
        self.assertEqual(counts["quizzes"], 1)
        self.assertEqual(counts["simulations"], 1)

    def test_last_7_days_excludes_older_simulations(self):
        twin = make_twin(self.user)
        self._simulation(self.user, twin)
        self._simulation(self.user, twin, days_ago=30)

        self.client.force_login(self.user)
        data = self.client.get(self.url).data

        self.assertEqual(data["counts"]["simulations"], 2)
        self.assertEqual(data["last_7_days_total"], 1)

    def test_weekly_chart_shape(self):
        self.client.force_login(self.user)
        weekly = self.client.get(self.url).data["weekly_simulations"]

        self.assertEqual(len(weekly), 7)
        self.assertEqual(set(weekly[0]), {"day", "count"})
        self.assertEqual(weekly[-1]["day"], timezone.now().strftime("%A"))

    def test_weekly_chart_counts_today(self):
        twin = make_twin(self.user)
        self._simulation(self.user, twin)

        self.client.force_login(self.user)
        weekly = self.client.get(self.url).data["weekly_simulations"]
        self.assertEqual(weekly[-1]["count"], 1)

    def test_last_twins_is_limited_to_three_and_newest_first(self):
        context = make_context(self.user)
        for i in range(4):
            make_twin(self.user, context=context, name=f"Twin {i}")

        self.client.force_login(self.user)
        last_twins = self.client.get(self.url).data["last_twins"]

        self.assertEqual(len(last_twins), 3)
        self.assertEqual(last_twins[0]["name"], "Twin 3")
        self.assertEqual(set(last_twins[0]), {"id", "name", "description", "average_grade"})
