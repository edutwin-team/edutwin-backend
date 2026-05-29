from django.db import models
from django.conf import settings


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