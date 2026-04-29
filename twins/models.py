from django.db import models
from django_enum import EnumField


# Create your models here.
#
#
#


class DifficultyPerceived(models.IntegerChoices):
    too_easy = 1
    easy = 2
    appropriate = 3
    hard = 4
    too_hard = 5


class Twin(models.Model):
    name = models.CharField(max_length=255)
    level = models.IntegerField(default=5)  # 1-10
    reading_speed = models.IntegerField(default=1.2)
    strong_domains = models.JSONField(default=list)  # ["math", "physics"]
    weak_domains = models.JSONField(default=list)  # ["history"]
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Twin: {self.name} (lvl {self.level})"


class TwinSimulation(models.Model):
    twin = models.ForeignKey(Twin, on_delete=models.CASCADE, related_name="simulations")
    content_type = models.CharField(max_length=50)  # "quiz" ou "course"
    content_id = models.IntegerField()
    simulated_score = models.IntegerField(null=True, blank=True)  # règles déterministes
    simulated_time_seconds = models.IntegerField(null=True, blank=True)
    difficulty_perception = models.IntegerField(
        choices=DifficultyPerceived.choices, null=True, blank=True
    )
    llm_feedback = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Simulation {self.twin.name} on {self.content_type}:{self.content_id}"
