from django.db.models import QuerySet, Avg
from quiz.models import Quiz, QuizAttempt


def get_active_quizzes() -> QuerySet[Quiz]:
    """Returns only quizzes that are currently active."""
    return Quiz.objects.filter(is_active=True).prefetch_related("questions")


def get_user_quiz_history(*, user) -> QuerySet[QuizAttempt]:
    """Returns a user's completed attempts sorted by date."""
    return (
        QuizAttempt.objects.filter(user=user, completed_at__isnull=False)
        .select_related("quiz")
        .order_by("-completed_at")
    )


def get_quiz_average_score(*, quiz_id: int) -> float:
    """Calculates the average score for a specific quiz."""
    result = QuizAttempt.objects.filter(
        quiz_id=quiz_id, completed_at__isnull=False
    ).aggregate(average=Avg("score"))

    return result["average"] or 0.0
