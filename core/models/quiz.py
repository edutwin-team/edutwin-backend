# core/models/quiz.py
from django.conf import settings
from django.db import models


class Quiz(models.Model):
    title = models.CharField(default="", max_length=255)
    description = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return str(self.title)


class QuizAttempt(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="attempts")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    score = models.FloatField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "quiz"],
                condition=models.Q(completed_at__isnull=True),
                name="unique_active_attempt_per_user_quiz",
            )
        ]

    @property
    def is_completed(self) -> bool:
        return self.completed_at is not None
