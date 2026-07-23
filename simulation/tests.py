import json
from unittest.mock import MagicMock, patch

import httpx
from django.test import TestCase
from django.urls import reverse
from groq import APIError, BadRequestError, RateLimitError
from rest_framework import status

from config.factories import (
    BaseAPITest,
    make_behavior,
    make_context,
    make_course,
    make_quiz,
    make_twin,
    make_user,
)
from twins.models import Objective
from . import engine, groq_client
from .models import SimulationResult

FAKE_QUIZ_JSON = json.dumps(
    {
        "answers": [
            {
                "question_title": "2+2 ?",
                "question_index": 1,
                "chosen_index": 1,
                "reasoning": "C'est évident",
                "improvement": "Consolider les additions simples avec des exercices chronométrés.",
            }
        ],
        "simulated_time_seconds": 120,
        "feedback": "Quiz facile.",
    }
)

FAKE_COURSE_JSON = json.dumps(
    {
        "comprehension_score": 72,
        "simulated_time_seconds": 240,
        "feedback": "Cours clair.",
    }
)


def httpx_response(code):
    return httpx.Response(code, request=httpx.Request("POST", "https://api.groq.com"))


# ---------------------------------------------------------
# ENGINE (déterministe, sans LLM)
# ---------------------------------------------------------
class EngineTests(TestCase):
    def setUp(self):
        self.user = make_user(email="engine@example.com")
        self.twin = make_twin(self.user)
        make_behavior(self.twin)
        self.quiz = make_quiz(self.user)
        self.course = make_course(self.user)

    def test_noise_is_seeded(self):
        self.assertEqual(engine._noise(42), engine._noise(42))
        self.assertLessEqual(abs(engine._noise(1, amplitude=5.0)), 5.0)

    def test_simulate_quiz_is_deterministic(self):
        first = engine.simulate_quiz(self.twin, self.quiz)
        second = engine.simulate_quiz(self.twin, self.quiz)
        self.assertEqual(first, second)

    def test_simulate_quiz_shape_and_bounds(self):
        result = engine.simulate_quiz(self.twin, self.quiz)
        self.assertEqual(
            set(result),
            {
                "simulated_score",
                "correct",
                "total",
                "simulated_time_seconds",
                "passed",
                "behavior_snapshot",
            },
        )
        self.assertGreaterEqual(result["simulated_score"], 0)
        self.assertLessEqual(result["simulated_score"], 100)
        self.assertEqual(result["total"], 1)
        self.assertGreaterEqual(result["simulated_time_seconds"], 30)
        self.assertIn("comprehension_level", result["behavior_snapshot"])

    def test_simulate_quiz_score_is_clamped_for_terrible_twin(self):
        bad_twin = make_twin(self.user, name="Nul")
        make_behavior(
            bad_twin,
            comprehension_level=0,
            motivation=0,
            learning_speed=0,
            error_rate=100,
            fatigue_level=100,
            attention_level=0,
            stress_level=100,
        )
        result = engine.simulate_quiz(bad_twin, self.quiz)
        self.assertGreaterEqual(result["simulated_score"], 0.0)
        self.assertFalse(result["passed"])

    def test_simulate_quiz_time_capped_by_limit(self):
        quiz = make_quiz(self.user, time_limit_minutes=1)
        self.assertLessEqual(
            engine.simulate_quiz(self.twin, quiz)["simulated_time_seconds"], 60
        )

    def test_simulate_quiz_without_questions(self):
        empty = make_quiz(self.user, with_questions=False)
        result = engine.simulate_quiz(self.twin, empty)
        self.assertEqual(result["total"], 1)  # division par zéro évitée via `or 1`

    def test_simulate_course_shape_and_determinism(self):
        first = engine.simulate_course(self.twin, self.course)
        self.assertEqual(first, engine.simulate_course(self.twin, self.course))
        self.assertEqual(
            set(first),
            {"simulated_score", "simulated_time_seconds", "behavior_snapshot"},
        )
        self.assertGreaterEqual(first["simulated_time_seconds"], 30)

    def test_simulate_course_with_empty_content(self):
        course = make_course(self.user, content="")
        self.assertGreaterEqual(
            engine.simulate_course(self.twin, course)["simulated_time_seconds"], 30
        )


# ---------------------------------------------------------
# GROQ CLIENT (LLM mocké — aucun appel réseau)
# ---------------------------------------------------------
class ExtractJsonTests(TestCase):
    def test_fenced_block(self):
        self.assertEqual(groq_client._extract_json('```json\n{"a": 1}\n```'), {"a": 1})

    def test_raw_object(self):
        self.assertEqual(groq_client._extract_json('bla {"a": 1} bla'), {"a": 1})

    def test_raw_array(self):
        self.assertEqual(groq_client._extract_json("[1, 2]"), [1, 2])

    def test_no_json_raises(self):
        with self.assertRaises(ValueError):
            groq_client._extract_json("aucun json ici")


class GetClientTests(TestCase):
    def setUp(self):
        groq_client._client = None
        self.addCleanup(setattr, groq_client, "_client", None)

    def test_missing_api_key_raises(self):
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(EnvironmentError):
                groq_client._get_client()

    def test_client_is_cached(self):
        with patch.dict("os.environ", {"GROQ_API_KEY": "fake"}):
            first = groq_client._get_client()
            self.assertIs(first, groq_client._get_client())


class ChatErrorHandlingTests(TestCase):
    def _client_raising(self, exc):
        client = MagicMock()
        client.chat.completions.create.side_effect = exc
        return client

    def test_returns_stripped_content(self):
        client = MagicMock()
        client.chat.completions.create.return_value.choices = [
            MagicMock(message=MagicMock(content="  hello  "))
        ]
        with patch.object(groq_client, "_get_client", return_value=client):
            self.assertEqual(groq_client._chat("prompt"), "hello")

    def test_none_content_becomes_empty_string(self):
        client = MagicMock()
        client.chat.completions.create.return_value.choices = [
            MagicMock(message=MagicMock(content=None))
        ]
        with patch.object(groq_client, "_get_client", return_value=client):
            self.assertEqual(groq_client._chat("prompt"), "")

    def test_context_length_bad_request_is_reraised(self):
        exc = BadRequestError(
            "maximum context length exceeded", response=httpx_response(400), body=None
        )
        with patch.object(
            groq_client, "_get_client", return_value=self._client_raising(exc)
        ):
            with self.assertRaises(BadRequestError):
                groq_client._chat("prompt")

    def test_other_bad_request_is_reraised(self):
        exc = BadRequestError("champ invalide", response=httpx_response(400), body=None)
        with patch.object(
            groq_client, "_get_client", return_value=self._client_raising(exc)
        ):
            with self.assertRaises(BadRequestError):
                groq_client._chat("prompt")

    def test_rate_limit_is_reraised(self):
        exc = RateLimitError("quota", response=httpx_response(429), body=None)
        with patch.object(
            groq_client, "_get_client", return_value=self._client_raising(exc)
        ):
            with self.assertRaises(RateLimitError):
                groq_client._chat("prompt")

    def test_generic_api_error_hits_undefined_name(self):
        """⚠️ BUG connu : `except groq.APIError` sans `import groq` → NameError."""
        exc = APIError(
            "boom", request=httpx.Request("POST", "https://api.groq.com"), body=None
        )
        with patch.object(
            groq_client, "_get_client", return_value=self._client_raising(exc)
        ):
            with self.assertRaises(NameError):
                groq_client._chat("prompt")


class PromptBuildersTests(TestCase):
    def setUp(self):
        self.user = make_user(email="prompt@example.com")
        self.context = make_context(self.user, name="Contexte X", subject="Physique")
        self.twin = make_twin(self.user, context=self.context, name="Alice")
        make_behavior(self.twin)

    def test_twin_profile_contains_key_data(self):
        Objective.objects.create(context=self.context, label="Maîtriser Newton")
        profile = groq_client._build_twin_profile(self.twin)
        self.assertIn("Alice", profile)
        self.assertIn("Contexte X", profile)
        self.assertIn("Physique", profile)
        self.assertIn("Maîtriser Newton", profile)

    def test_twin_profile_without_objectives(self):
        self.assertIn("Aucun objectif", groq_client._build_twin_profile(self.twin))

    def test_questions_block_numbering(self):
        quiz = make_quiz(self.user)
        block = groq_client._build_questions_block(list(quiz.questions.all()))
        self.assertIn("Q1", block)
        self.assertIn("1. 4", block)
        self.assertIn("2. 5", block)


class ScoreQuizAnswersTests(TestCase):
    def setUp(self):
        self.user = make_user(email="score@example.com")
        self.questions = list(make_quiz(self.user).questions.all())

    def test_correct_answer(self):
        result = groq_client.score_quiz_answers(
            self.questions, [{"question_index": 1, "chosen_index": 1}]
        )
        self.assertEqual(result["simulated_score"], 100.0)
        self.assertEqual(result["correct"], 1)
        self.assertTrue(result["passed"])

    def test_wrong_answer(self):
        result = groq_client.score_quiz_answers(
            self.questions, [{"question_index": 1, "chosen_index": 2}]
        )
        self.assertEqual(result["simulated_score"], 0.0)
        self.assertFalse(result["passed"])

    def test_out_of_range_index_is_ignored(self):
        result = groq_client.score_quiz_answers(
            self.questions, [{"question_index": 1, "chosen_index": 99}]
        )
        self.assertEqual(result["correct"], 0)

    def test_missing_answer_is_skipped(self):
        self.assertEqual(
            groq_client.score_quiz_answers(self.questions, [])["correct"], 0
        )

    def test_no_questions_returns_zero(self):
        result = groq_client.score_quiz_answers([], [])
        self.assertEqual(result["simulated_score"], 0.0)
        self.assertEqual(result["total"], 0)

    def test_default_passing_score(self):
        self.assertEqual(groq_client.quiz_passing_score_from_context([]), 50)


class LLMPipelineTests(TestCase):
    def setUp(self):
        self.user = make_user(email="pipe@example.com")
        self.twin = make_twin(self.user)
        make_behavior(self.twin)
        self.quiz = make_quiz(self.user)
        self.course = make_course(self.user)

    def test_take_quiz_without_questions_raises(self):
        empty = make_quiz(self.user, with_questions=False)
        with self.assertRaises(ValueError):
            groq_client.take_quiz_as_twin(self.twin, empty)

    def test_simulate_quiz_with_llm(self):
        with patch.object(groq_client, "_chat", return_value=FAKE_QUIZ_JSON):
            result = groq_client.simulate_quiz_with_llm(self.twin, self.quiz)
        self.assertEqual(result["simulated_score"], 100.0)
        self.assertEqual(result["simulated_time_seconds"], 120)
        self.assertEqual(result["feedback"], "Quiz facile.")
        self.assertTrue(result["passed"])
        self.assertEqual(len(result["llm_answers"]), 1)
        self.assertIn("comprehension_level", result["behavior_snapshot"])

    def test_llm_answer_carries_improvement_axis(self):
        with patch.object(groq_client, "_chat", return_value=FAKE_QUIZ_JSON):
            result = groq_client.simulate_quiz_with_llm(self.twin, self.quiz)
        answer = result["llm_answers"][0]
        self.assertIn("improvement", answer)
        self.assertIn("Consolider", answer["improvement"])

    def test_missing_improvement_defaults_to_empty_string(self):
        # LLM omet le champ → le pipeline le garantit quand mêmeEDT-78 Simulation
        without = json.dumps(
            {
                "answers": [
                    {
                        "question_title": "2+2 ?",
                        "question_index": 1,
                        "chosen_index": 1,
                        "reasoning": "ok",
                    }
                ],
                "simulated_time_seconds": 60,
                "feedback": "f",
            }
        )
        with patch.object(groq_client, "_chat", return_value=without):
            result = groq_client.simulate_quiz_with_llm(self.twin, self.quiz)
        self.assertEqual(result["llm_answers"][0]["improvement"], "")

    def test_simulate_quiz_with_invalid_json_raises(self):
        with patch.object(groq_client, "_chat", return_value="pas de json"):
            with self.assertRaises(ValueError):
                groq_client.simulate_quiz_with_llm(self.twin, self.quiz)

    def test_simulate_course_with_llm(self):
        with patch.object(groq_client, "_chat", return_value=FAKE_COURSE_JSON):
            result = groq_client.simulate_course_with_llm(self.twin, self.course)
        self.assertEqual(result["simulated_score"], 72.0)
        self.assertEqual(result["simulated_time_seconds"], 240)
        self.assertEqual(result["feedback"], "Cours clair.")

    def test_simulate_course_uses_defaults_on_partial_json(self):
        with patch.object(groq_client, "_chat", return_value="{}"):
            result = groq_client.simulate_course_with_llm(self.twin, self.course)
        self.assertEqual(result["simulated_score"], 50.0)
        self.assertEqual(result["simulated_time_seconds"], 300)
        self.assertEqual(result["feedback"], "")

    def test_simulate_course_with_invalid_json_raises(self):
        with patch.object(groq_client, "_chat", return_value="rien"):
            with self.assertRaises(ValueError):
                groq_client.simulate_course_with_llm(self.twin, self.course)


# ---------------------------------------------------------
# MODEL
# ---------------------------------------------------------
class SimulationResultModelTests(TestCase):
    def setUp(self):
        self.user = make_user(email="model@example.com")
        self.twin = make_twin(self.user, name="Alice")
        self.quiz = make_quiz(self.user, title="Quiz A")

    def _make(self, **kw):
        defaults = dict(
            user=self.user,
            twin=self.twin,
            simulation_type=SimulationResult.SimulationType.QUIZ,
            quiz=self.quiz,
            simulated_score=80.0,
            simulated_time_seconds=100,
        )
        defaults.update(kw)
        return SimulationResult.objects.create(**defaults)

    def test_str(self):
        self.assertIn("Alice", str(self._make()))
        self.assertIn("quiz", str(self._make()))

    def test_ordering_is_newest_first(self):
        old = self._make()
        new = self._make()
        self.assertEqual(
            list(SimulationResult.objects.all())[0].pk, max(old.pk, new.pk)
        )

    def test_quiz_deletion_sets_null(self):
        result = self._make()
        self.quiz.delete()
        result.refresh_from_db()
        self.assertIsNone(result.quiz)

    def test_twin_deletion_cascades(self):
        self._make()
        self.twin.delete()
        self.assertEqual(SimulationResult.objects.count(), 0)


# ---------------------------------------------------------
# VIEWS
# ---------------------------------------------------------
class SimulateQuizViewTests(BaseAPITest):
    def setUp(self):
        super().setUp()
        self.user = make_user(email="simquiz@example.com")
        self.other = make_user(email="simother@example.com")
        self.twin = make_twin(self.user)
        make_behavior(self.twin)
        self.quiz = make_quiz(self.user)
        self.url = reverse("simulate-quiz")
        self.client.force_login(self.user)

    def _payload(self, **kw):
        return {"twin_id": self.twin.pk, "quiz_id": self.quiz.pk, **kw}

    def test_requires_authentication(self):
        self.client.logout()
        self.assertEqual(
            self.client.post(self.url, self._payload(), format="json").status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_invalid_payload(self):
        res = self.client.post(self.url, {"twin_id": "abc"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_twin_of_another_user_is_404(self):
        foreign = make_twin(self.other)
        res = self.client.post(
            self.url, self._payload(twin_id=foreign.pk), format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_unknown_quiz_is_404(self):
        res = self.client.post(self.url, self._payload(quiz_id=999999), format="json")
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_twin_without_behavior_is_422(self):
        naked = make_twin(self.user, name="Sans comportement")
        res = self.client.post(self.url, self._payload(twin_id=naked.pk), format="json")
        self.assertEqual(res.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertIn("Behavior", res.data["detail"])

    @patch(
        "simulation.views.simulate_quiz_with_llm",
        side_effect=ValueError("no questions"),
    )
    def test_value_error_is_422(self, _mock):
        res = self.client.post(self.url, self._payload(), format="json")
        self.assertEqual(res.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)

    @patch(
        "simulation.views.simulate_quiz_with_llm",
        side_effect=EnvironmentError("GROQ_API_KEY is not set"),
    )
    def test_environment_error_is_503(self, _mock):
        res = self.client.post(self.url, self._payload(), format="json")
        self.assertEqual(res.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)

    def test_success_persists_result(self):
        fake = {
            "simulated_score": 80.0,
            "correct": 4,
            "total": 5,
            "simulated_time_seconds": 120,
            "passed": True,
            "feedback": "ok",
            "behavior_snapshot": {
                "comprehension_level": 70,
                "motivation": 60,
                "fatigue_level": 30,
            },
            "llm_answers": [
                {
                    "question_index": 1,
                    "question_title": "2+2 ?",
                    "chosen_index": 1,
                    "reasoning": "évident",
                    "improvement": "Réviser les tables d'addition.",
                }
            ],
        }
        with patch("simulation.views.simulate_quiz_with_llm", return_value=fake):
            res = self.client.post(self.url, self._payload(), format="json")

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["quiz_title"], self.quiz.title)
        self.assertEqual(res.data["twin_name"], self.twin.name)
        # L'axe d'amélioration est exposé au front dans la réponse
        self.assertEqual(
            res.data["llm_answers"][0]["improvement"], "Réviser les tables d'addition."
        )

        saved = SimulationResult.objects.get()
        self.assertEqual(saved.user, self.user)
        # ... et persisté dans answer_details pour l'historique
        self.assertEqual(
            saved.answer_details[0]["improvement"], "Réviser les tables d'addition."
        )
        self.assertEqual(saved.simulation_type, "quiz")
        self.assertEqual(saved.simulated_score, 80.0)


class SimulateCourseViewTests(BaseAPITest):
    def setUp(self):
        super().setUp()
        self.user = make_user(email="simcourse@example.com")
        self.twin = make_twin(self.user)
        make_behavior(self.twin)
        self.course = make_course(self.user)
        self.url = reverse("simulate-course")
        self.client.force_login(self.user)

    def _payload(self, **kw):
        return {"twin_id": self.twin.pk, "course_id": self.course.pk, **kw}

    def test_invalid_payload(self):
        res = self.client.post(self.url, {}, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unknown_course_is_404(self):
        res = self.client.post(self.url, self._payload(course_id=999999), format="json")
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_twin_without_behavior_is_422(self):
        naked = make_twin(self.user, name="Sans")
        res = self.client.post(self.url, self._payload(twin_id=naked.pk), format="json")
        self.assertEqual(res.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)

    @patch(
        "simulation.views.simulate_course_with_llm", side_effect=ValueError("bad json")
    )
    def test_value_error_is_422(self, _mock):
        res = self.client.post(self.url, self._payload(), format="json")
        self.assertEqual(res.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)

    @patch(
        "simulation.views.simulate_course_with_llm",
        side_effect=EnvironmentError("no key"),
    )
    def test_environment_error_is_503(self, _mock):
        res = self.client.post(self.url, self._payload(), format="json")
        self.assertEqual(res.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)

    def test_success_persists_result(self):
        fake = {
            "simulated_score": 65.0,
            "simulated_time_seconds": 200,
            "feedback": "clair",
            "behavior_snapshot": {
                "comprehension_level": 70,
                "motivation": 60,
                "fatigue_level": 30,
            },
        }
        with patch("simulation.views.simulate_course_with_llm", return_value=fake):
            res = self.client.post(self.url, self._payload(), format="json")

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        saved = SimulationResult.objects.get()
        self.assertEqual(saved.simulation_type, "course")
        self.assertIsNone(saved.passed)
        self.assertEqual(saved.course, self.course)


class SimulationHistoryTests(BaseAPITest):
    def setUp(self):
        super().setUp()
        self.user = make_user(email="hist@example.com")
        self.other = make_user(email="histother@example.com")
        self.twin_a = make_twin(self.user, name="A")
        self.twin_b = make_twin(self.user, name="B")
        self.quiz = make_quiz(self.user)
        self.course = make_course(self.user)
        self.url = reverse("simulation-history")

        SimulationResult.objects.create(
            user=self.user,
            twin=self.twin_a,
            simulation_type="quiz",
            quiz=self.quiz,
            simulated_score=50.0,
            simulated_time_seconds=60,
        )
        SimulationResult.objects.create(
            user=self.user,
            twin=self.twin_b,
            simulation_type="course",
            course=self.course,
            simulated_score=70.0,
            simulated_time_seconds=90,
        )
        SimulationResult.objects.create(
            user=self.other,
            twin=make_twin(self.other),
            simulation_type="quiz",
            simulated_score=10.0,
            simulated_time_seconds=10,
        )
        self.client.force_login(self.user)

    def test_requires_authentication(self):
        self.client.logout()
        self.assertEqual(
            self.client.get(self.url).status_code, status.HTTP_403_FORBIDDEN
        )

    def test_scoped_to_current_user(self):
        self.assertEqual(len(self.client.get(self.url).data), 2)

    def test_filter_by_twin(self):
        res = self.client.get(self.url, {"twin_id": self.twin_a.pk})
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["twin_name"], "A")

    def test_filter_by_type(self):
        self.assertEqual(len(self.client.get(self.url, {"type": "course"}).data), 1)
        self.assertEqual(len(self.client.get(self.url, {"type": "quiz"}).data), 1)

    def test_unknown_type_filter_is_ignored(self):
        self.assertEqual(len(self.client.get(self.url, {"type": "banane"}).data), 2)

    def test_serializer_exposes_related_titles(self):
        res = self.client.get(self.url, {"type": "quiz"})
        self.assertEqual(res.data[0]["quiz_title"], self.quiz.title)
