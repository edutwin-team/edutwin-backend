from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator

#todo: add validation in all models for special characters (/*-:; ...)

#enums
class PreferredContentType(models.TextChoices):
    TEXT = "text", "Texte"
    VIDEO = "video", "Vidéo"
    QUIZ = "quiz", "Quiz"
    IMAGE = "image", "Image"
    INTERACTIVE = "interactive", "Interactif"
    MIXED = "mixed", "Mixte"
    
class LearningStyle(models.TextChoices):
    VISUAL = "visual", "Visuel"
    PRACTICAL = "practical", "Pratique"
    THEORETICAL = "theoretical", "Théorique"
    EXERCISE_BASED = "exercise_based", "Basé sur exercices"
    MIXED = "mixed", "Mixte"
    
#db models
class PedagogicalContext(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="contexts"
    )

    name = models.CharField(max_length=255)
    subject = models.CharField(max_length=255)
    level = models.CharField(max_length=100)
    school = models.CharField(max_length=255)
    country = models.CharField(max_length=100)
    academic_year = models.CharField(max_length=20)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name


class Objective(models.Model):
    context = models.ForeignKey(
        PedagogicalContext,
        on_delete=models.CASCADE,
        related_name="objectives"
    )

    label = models.CharField(max_length=255)

    def __str__(self):
        return self.label
    
class DigitalTwin(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="twins"
    )

    context = models.ForeignKey(
        "PedagogicalContext",
        on_delete=models.CASCADE,
        related_name="twins"
    )

    name = models.CharField(max_length=255)
    age = models.IntegerField(
        validators=[MinValueValidator(10), MaxValueValidator(100)]
    )

    average_grade = models.FloatField(
        validators=[MinValueValidator(0), MaxValueValidator(20)]
    )

    description = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Behavior(models.Model):
    twin = models.OneToOneField(
        DigitalTwin,
        on_delete=models.CASCADE,
        related_name="behavior"
    )

    comprehension_level = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )

    motivation = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )

    learning_speed = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )

    error_rate = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )

    learning_style = models.CharField(
    max_length=20,
    choices=LearningStyle.choices,
    default=LearningStyle.MIXED
)

    fatigue_level = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )

    attention_level = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )

    stress_level = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )

    curiosity_level = models.IntegerField(
        default=50,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )

    autonomy_level = models.IntegerField(
        default=50,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )

    persistence_level = models.IntegerField(
        default=50,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )

    memory_retention = models.IntegerField(
        default=50,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )

    preferred_content_type = models.CharField(
        max_length=20,
        choices=PreferredContentType.choices,
        default=PreferredContentType.MIXED
    )

    question_frequency = models.IntegerField(default=0)

    comment = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Behavior of {self.twin.name}"