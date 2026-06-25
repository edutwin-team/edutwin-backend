from django.db import models

from django.conf import settings



#enums

class QuestionType(models.TextChoices):
    SINGLE_CHOICE = "single_choice", "Single choice"
    MULTIPLE_CHOICE = "multiple_choice", "Multiple choice"
    TRUE_FALSE = "true_false", "True / False"
    
class DifficultyLevel(models.TextChoices):
    EASY = "easy", "Easy"
    MEDIUM = "medium", "Medium"
    HARD = "hard", "Hard"


class ContentSourceType(models.TextChoices):
    MANUAL = "manual", "Manual"
    IMPORT_FILE = "import_file", "Import File"


#course model (not used for mvp)

class Course(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="courses",
        
    )

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    content = models.TextField()

    source_type = models.CharField(
        max_length=20,
        choices=ContentSourceType.choices,
        default=ContentSourceType.MANUAL
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


#quiz model

class Quiz(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="quizzes",
    )

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)

    passing_score = models.IntegerField(default=50)
    time_limit_minutes = models.IntegerField(default=15)

    source_type = models.CharField(
        max_length=20,
        choices=ContentSourceType.choices,
        default=ContentSourceType.MANUAL
    )

    # a quiz can be independent or related to a course
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="quizzes",
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


#quition model

class Question(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="questions")
    text = models.TextField()
    question_type = models.CharField(
        max_length=30,
        choices=QuestionType.choices,
        default=QuestionType.SINGLE_CHOICE
    )

    difficulty_level = models.CharField(
        max_length=20,
        choices=DifficultyLevel.choices,
        default=DifficultyLevel.MEDIUM
    )
   

    def __str__(self):
        return f"Question: {self.text}"


# answer model

class Answer(models.Model):
    question = models.ForeignKey(
        Question, on_delete=models.CASCADE, related_name="answers"
    )
    text = models.CharField(max_length=500)
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return f"Answer: {self.text} ({'correct' if self.is_correct else 'wrong'})"
