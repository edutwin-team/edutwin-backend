from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator


class SimulationResult(models.Model):
    """Persists every simulation run for history/analytics."""

    class SimulationType(models.TextChoices):
        QUIZ = "quiz", "Quiz"
        COURSE = "course", "Course"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="simulation_results",
    )

    twin = models.ForeignKey(
        "twins.DigitalTwin",
        on_delete=models.CASCADE,
        related_name="simulation_results",
    )

    simulation_type = models.CharField(
        max_length=10,
        choices=SimulationType.choices,
    )

    # Generic FK to either Quiz or Course (store id + type)
    quiz = models.ForeignKey(
        "content.Quiz",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="simulation_results",
    )
    answer_details = models.JSONField(default=list, blank=True)
    course = models.ForeignKey(
        "content.Course",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="simulation_results",
    )

    simulated_score = models.FloatField(
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    simulated_time_seconds = models.IntegerField()
    passed = models.BooleanField(null=True, blank=True)  # null for course
    correct = models.IntegerField(null=True, blank=True)  # null for course
    total = models.IntegerField(null=True, blank=True)  # null for course

    feedback = models.TextField(blank=True)

    # Snapshot of behavior at time of simulation
    behavior_snapshot = models.JSONField(default=dict)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        target = self.quiz or self.course
        return f"[{self.simulation_type}] {self.twin.name} → {target} ({self.simulated_score}/100)"
