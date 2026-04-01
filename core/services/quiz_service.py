from django.db import IntegrityError, transaction
from django.utils import timezone

from core.models import Quiz, QuizAttempt, Choice


@transaction.atomic
def start_quiz_attempt(*, user, quiz_id: int) -> QuizAttempt:
    quiz = Quiz.objects.get(id=quiz_id, is_active=True)

    try:
        return QuizAttempt.objects.create(user=user, quiz=quiz)
    except IntegrityError:
        raise ValueError("You already have an active attempt for this quiz.")


def compute_score(quiz: Quiz, user_answers: dict[int, int | None]) -> float:
    """
    user_answers: {question_id: choice_id}
    Returns a normalised score between 0.0 and 1.0.
    """
    question_ids = set(quiz.questions.values_list("id", flat=True))
    total = len(question_ids)
    if total == 0:
        return 0.0

    submitted_pairs = {
        int(question_id): int(choice_id)
        for question_id, choice_id in user_answers.items()
        if choice_id is not None and int(question_id) in question_ids
    }

    correct_pairs = set(
        Choice.objects.filter(
            question__quiz=quiz,
            is_correct=True,
        ).values_list("question_id", "id")
    )

    correct_count = sum(
        1
        for question_id, choice_id in submitted_pairs.items()
        if (question_id, choice_id) in correct_pairs
    )

    return round(correct_count / total, 4)


@transaction.atomic
def grade_quiz_attempt(
    *, attempt_id: int, user_answers: dict[int, int | None]
) -> QuizAttempt:
    attempt = (
        QuizAttempt.objects.select_for_update()
        .select_related("quiz")
        .get(id=attempt_id)
    )

    if attempt.completed_at is not None:
        raise ValueError("This attempt has already been completed.")

    attempt.score = compute_score(attempt.quiz, user_answers)
    attempt.completed_at = timezone.now()
    attempt.save(update_fields=["score", "completed_at"])

    return attempt
