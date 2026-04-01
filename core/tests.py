from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import AccessToken

from core.models import Quiz, QuizAttempt, Question, Choice

User = get_user_model()


class QuizApiTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="alice",
            email="alice@example.com",
            password="StrongPassword123!",
        )

        cls.quiz = Quiz.objects.create(
            title="Python Basics",
            description="Small quiz",
            is_active=True,
        )

        cls.q1 = Question.objects.create(
            quiz=cls.quiz,
            text="What is Django?",
            order=1,
        )
        cls.q2 = Question.objects.create(
            quiz=cls.quiz,
            text="What is DRF?",
            order=2,
        )

        cls.q1_correct = Choice.objects.create(
            question=cls.q1,
            text="A Python web framework",
            is_correct=True,
        )
        cls.q1_wrong = Choice.objects.create(
            question=cls.q1,
            text="A database",
            is_correct=False,
        )

        cls.q2_correct = Choice.objects.create(
            question=cls.q2,
            text="Django REST Framework",
            is_correct=True,
        )
        cls.q2_wrong = Choice.objects.create(
            question=cls.q2,
            text="A CSS library",
            is_correct=False,
        )

    def authenticate(self):
        self.client.force_authenticate(user=self.user)

    def auth_me_url(self):
        return reverse("auth-me")

    def start_attempt_url(self, quiz_id: int):
        return reverse("quiz-start-attempt", kwargs={"quiz_id": quiz_id})

    def submit_attempt_url(self, attempt_id: int):
        return reverse("quiz-submit-attempt", kwargs={"attempt_id": attempt_id})

    def test_auth_me_requires_authentication(self):
        response = self.client.get(self.auth_me_url(), format="json")

        self.assertIn(
            response.status_code,
            {status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN},
        )

    def test_auth_me_returns_current_user(self):
        self.authenticate()

        response = self.client.get(self.auth_me_url(), format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["username"], self.user.username)
        self.assertEqual(response.data["email"], self.user.email)

    def test_start_quiz_attempt_creates_attempt(self):
        self.authenticate()

        response = self.client.post(
            self.start_attempt_url(self.quiz.id),
            {},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(QuizAttempt.objects.count(), 1)

        attempt = QuizAttempt.objects.get()
        self.assertEqual(attempt.user, self.user)
        self.assertEqual(attempt.quiz, self.quiz)
        self.assertIsNone(attempt.score)
        self.assertIsNone(attempt.completed_at)

        self.assertEqual(response.data["id"], attempt.id)
        self.assertEqual(response.data["quiz_id"], self.quiz.id)
        self.assertEqual(response.data["user_id"], self.user.id)

    def test_start_quiz_attempt_rejects_second_active_attempt(self):
        self.authenticate()

        first = self.client.post(
            self.start_attempt_url(self.quiz.id),
            {},
            format="json",
        )
        second = self.client.post(
            self.start_attempt_url(self.quiz.id),
            {},
            format="json",
        )

        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(QuizAttempt.objects.count(), 1)

    def test_submit_quiz_attempt_grades_correctly(self):
        self.authenticate()

        start_response = self.client.post(
            self.start_attempt_url(self.quiz.id),
            {},
            format="json",
        )
        self.assertEqual(start_response.status_code, status.HTTP_201_CREATED)

        attempt_id = start_response.data["id"]

        payload = {
            "answers": {
                str(self.q1.id): self.q1_correct.id,
                str(self.q2.id): self.q2_correct.id,
            }
        }

        response = self.client.post(
            self.submit_attempt_url(attempt_id),
            payload,
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["score"], 1.0)

        attempt = QuizAttempt.objects.get(id=attempt_id)
        self.assertEqual(attempt.score, 1.0)
        self.assertIsNotNone(attempt.completed_at)

    def test_submit_quiz_attempt_partial_score(self):
        self.authenticate()

        start_response = self.client.post(
            self.start_attempt_url(self.quiz.id),
            {},
            format="json",
        )
        self.assertEqual(start_response.status_code, status.HTTP_201_CREATED)

        attempt_id = start_response.data["id"]

        payload = {
            "answers": {
                str(self.q1.id): self.q1_correct.id,
                str(self.q2.id): self.q2_wrong.id,
            }
        }

        response = self.client.post(
            self.submit_attempt_url(attempt_id),
            payload,
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["score"], 0.5)

    def test_submit_quiz_attempt_cannot_be_done_twice(self):
        self.authenticate()

        start_response = self.client.post(
            self.start_attempt_url(self.quiz.id),
            {},
            format="json",
        )
        self.assertEqual(start_response.status_code, status.HTTP_201_CREATED)

        attempt_id = start_response.data["id"]

        payload = {
            "answers": {
                str(self.q1.id): self.q1_correct.id,
                str(self.q2.id): self.q2_correct.id,
            }
        }

        first = self.client.post(
            self.submit_attempt_url(attempt_id),
            payload,
            format="json",
        )
        second = self.client.post(
            self.submit_attempt_url(attempt_id),
            payload,
            format="json",
        )

        self.assertEqual(first.status_code, status.HTTP_200_OK)
        self.assertEqual(second.status_code, status.HTTP_400_BAD_REQUEST)
