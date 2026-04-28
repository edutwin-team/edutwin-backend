from django.db import models
from django_enum import EnumField
from enum import IntEnum


class ContentType(IntEnum):
    course = 1
    quiz = 2


class QuestionType(IntEnum):
    single_choice = 1
    multiple_choice = 2
    true_false = 3


class Content(models.Model):
    content_type = EnumField(ContentType)
    title = models.CharField(max_length=255)
    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True  # NE PAS SUPRIMER == EMPECHE CREATION DE CLASSE


class Course(Content):
    description = models.TextField()
    body = models.TextField()

    def __str__(self):
        return f"Course: {self.title}"


class Quiz(Content):
    passing_score = models.IntegerField(default=50)
    time_limit_minutes = models.IntegerField(default=15)

    def __str__(self):
        return f"Quiz: {self.title}"


class Question(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="questions")
    title = models.CharField(max_length=500)
    question_type = EnumField(QuestionType, default=QuestionType.single_choice)

    def __str__(self):
        return f"Question: {self.title}"


class Answer(models.Model):
    question = models.ForeignKey(
        Question, on_delete=models.CASCADE, related_name="answers"
    )
    text = models.CharField(max_length=500)
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return f"Answer: {self.text} ({'correct' if self.is_correct else 'wrong'})"
